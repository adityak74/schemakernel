import streamlit as st
import os
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
    st.set_page_config(page_title="AI Patient Intake", page_icon="🤖")
    st.title("🤖 AI-Planned Patient Intake")
    st.markdown("""
        In this version, **the AI is the architect**. 
        
        There is no hardcoded logic for follow-up questions. Instead, the AI analyzes 
        the answers against the `PolicyConfig` and dynamically decides what to ask next.
    """)

    # --- 1. Define the System Policy ---
    # This is where you tell the AI "what" you want to achieve, not "how" to do it.
    policy = PolicyConfig(
        reasoning_style="thorough and empathetic",
        baseline_questions=[
            FieldDefinition(key="name", label="Legal Name", type=FieldType.TEXT, required=True),
            FieldDefinition(key="reason", label="Reason for visit", type=FieldType.TEXTAREA, required=True),
        ],
        glossary={
            "Triage": "The process of determining the priority of patients' treatments.",
            "HIPAA": "Health Insurance Portability and Accountability Act."
        },
        prohibited_topics=["financial advice", "non-medical gossip"],
        completion_criteria={
            "custom_description": "Collect enough info to understand the patient's immediate concern and medical history relevant to that concern."
        }
    )

    # --- 2. Setup SchemaKernel ---
    SESSION_ID = "ai-intake-session"
    store = StreamlitSessionStore(key_prefix="ai_demo_")
    adapter = StreamlitFormAdapter()
    
    # create_workflow will now use the REAL PlannerClient (LLM)
    # because we aren't passing a mock.
    try:
        workflow = create_workflow(
            policy=policy,
            store=store
        )
    except Exception as e:
        st.error(f"Failed to initialize AI Planner: {e}")
        st.info("Ensure ANTHROPIC_API_KEY or OPENAI_API_KEY is set in your environment.")
        return

    # --- 3. Manage State ---
    try:
        state = workflow.get_state(SESSION_ID)
    except Exception:
        state = workflow.start_session(SESSION_ID)

    # --- 4. Completion Check ---
    if state.stage == WorkflowStage.COMPLETE:
        st.success("✅ AI has determined the intake is complete.")
        st.json(state.answers)
        if st.button("Start New Intake"):
            store.delete_state(SESSION_ID)
            st.rerun()
        return

    # --- 5. Adaptive Logic ---
    unanswered = [k for k in state.field_order if k not in state.answers]
    
    if not unanswered:
        with st.status("🧠 AI is analyzing your answers...", expanded=True) as status:
            try:
                # This calls the LLM!
                workflow.run_planner_turn(SESSION_ID)
                status.update(label="AI has updated the form requirements.", state="complete")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                status.update(label="AI Error", state="error")
                st.error(f"The AI Planner encountered an issue: {e}")
                st.stop()

    # --- 6. Render ---
    st.subheader("Current Form")
    active_fields = [state.fields[k] for k in unanswered]
    
    new_answers = adapter.render_step(
        fields=active_fields,
        current_answers=state.answers,
        form_key="ai_intake_form"
    )

    if new_answers:
        for k, v in new_answers.items():
            workflow.submit_answer(SESSION_ID, k, v)
        st.rerun()

    # Debug
    with st.sidebar:
        st.write("### AI Workflow Debug")
        st.write(f"Turns: `{state.turn_count}`")
        st.write(f"Model: `{policy.model}`")
        if st.button("Reset AI Session"):
            store.delete_state(SESSION_ID)
            st.rerun()

if __name__ == "__main__":
    main()
