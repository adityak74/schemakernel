import streamlit as st
from schemakernel import (
    create_workflow,
    StreamlitSessionStore,
    StreamlitFormAdapter,
    PolicyConfig,
    FieldDefinition,
    FieldType,
    WorkflowStage,
)
import time

def main():
    st.set_page_config(page_title="Ollama Adaptive Form", page_icon="🦙")
    st.title("🦙 Ollama-Powered Adaptive Form")
    st.markdown("""
        This version uses **local Ollama** to drive the form planning. 
        Ensure you have Ollama running locally with `ollama run llama3`.
    """)

    # --- 1. Define the System Policy for Ollama ---
    policy = PolicyConfig(
        provider="ollama",
        model="gemma4:26b",  # Updated per user request
        base_url="http://localhost:11434/v1",
        reasoning_style="concise and direct",
        baseline_questions=[
            FieldDefinition(key="user_goal", label="What are you looking for today?", type=FieldType.TEXT, required=True),
        ],
        completion_criteria={
            "custom_description": "Stop once the user's specific request is clarified."
        }
    )

    # --- 2. Setup SchemaKernel ---
    SESSION_ID = "ollama-session"
    store = StreamlitSessionStore(key_prefix="ollama_")
    adapter = StreamlitFormAdapter()
    
    try:
        workflow = create_workflow(
            policy=policy,
            store=store
        )
    except Exception as e:
        st.error(f"Failed to initialize Ollama Planner: {e}")
        return

    # --- 3. Manage State ---
    try:
        state = workflow.get_state(SESSION_ID)
    except Exception:
        state = workflow.start_session(SESSION_ID)

    # --- 4. Completion Check ---
    if state.stage == WorkflowStage.COMPLETE:
        st.success("✅ Ollama has completed the flow.")
        st.json(state.answers)
        if st.button("Start New Session"):
            store.delete_state(SESSION_ID)
            st.rerun()
        return

    # --- 5. Adaptive Logic ---
    unanswered = [k for k in state.field_order if k not in state.answers]
    
    if not unanswered:
        with st.status("🦙 Ollama is thinking...", expanded=True) as status:
            try:
                workflow.run_planner_turn(SESSION_ID)
                status.update(label="Ollama has updated the form.", state="complete")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                status.update(label="Ollama Error", state="error")
                st.error(f"Error: {e}")
                st.info("Make sure Ollama is running: `ollama serve`")
                st.stop()

    # --- 6. Render ---
    st.subheader("Current Questions")
    active_fields = [state.fields[k] for k in unanswered]
    
    new_answers = adapter.render_step(
        fields=active_fields,
        current_answers=state.answers,
        form_key="ollama_form"
    )

    if new_answers:
        for k, v in new_answers.items():
            workflow.submit_answer(SESSION_ID, k, v)
        st.rerun()

    # Debug
    with st.sidebar:
        st.write("### Ollama Debug")
        st.write(f"Turns: `{state.turn_count}`")
        st.write(f"Model: `{policy.model}`")
        if st.button("Reset Session"):
            store.delete_state(SESSION_ID)
            st.rerun()

if __name__ == "__main__":
    main()
