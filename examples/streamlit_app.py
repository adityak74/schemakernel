import streamlit as st
from schemakernel import (
    create_workflow,
    StreamlitSessionStore,
    StreamlitFormAdapter,
    PlannerResponse,
    PlannerAction,
    ActionType,
    FieldDefinition,
    FieldType,
    CompletionStatus,
)
import time

# --- Mock Planner Implementation ---
# A simple hardcoded planner to simulate adaptive field generation without LLM.
class MockPatientPlanner:
    def plan(self, state, traces):
        """
        Simulates an adaptive intake process.
        - First step: Ask for Name and Age.
        - Second step (if Age > 18): Ask for Occupation.
        - Second step (if Age <= 18): Ask for School and Grade.
        - Final step: Complete.
        """
        data = state.captured_data
        
        # Initial fields
        if not data:
            return PlannerResponse(
                action=PlannerAction(
                    type=ActionType.PROMPT,
                    fields=[
                        FieldDefinition(key="name", label="Full Name", type=FieldType.TEXT, required=True),
                        FieldDefinition(key="age", label="Age", type=FieldType.INTEGER, required=True),
                    ]
                )
            )

        # Conditional fields based on age
        if "name" in data and "age" in data:
            if data["age"] > 18:
                if "occupation" not in data:
                    return PlannerResponse(
                        action=PlannerAction(
                            type=ActionType.PROMPT,
                            fields=[
                                FieldDefinition(key="occupation", label="Occupation", type=FieldType.TEXT),
                            ]
                        )
                    )
            else:
                if "school" not in data:
                    return PlannerResponse(
                        action=PlannerAction(
                            type=ActionType.PROMPT,
                            fields=[
                                FieldDefinition(key="school", label="School Name", type=FieldType.TEXT),
                                FieldDefinition(key="grade", label="Grade", type=FieldType.INTEGER),
                            ]
                        )
                    )

        # Completion
        return PlannerResponse(
            action=PlannerAction(type=ActionType.COMPLETE),
            status=CompletionStatus.COMPLETED
        )

# --- Streamlit UI logic ---

def main():
    st.title("🏥 Patient Intake (SchemaKernel Demo)")
    st.markdown("""
        This demo uses `schemakernel` to manage an adaptive form flow. 
        The fields shown depend on your previous answers.
    """)

    # 1. Initialize SchemaKernel Components
    # We use StreamlitSessionStore to persist workflow state in st.session_state
    store = StreamlitSessionStore(key_prefix="sk_demo_")
    adapter = StreamlitFormAdapter()
    
    # Simple factory-based creation
    workflow = create_workflow(
        planner=MockPatientPlanner(),
        store=store,
        session_id="patient-intake-session"
    )

    # 2. Check if the workflow is already complete
    try:
        outcome = workflow.get_outcome()
        st.success("✅ Intake Complete!")
        st.json(outcome.final_data)
        if st.button("Restart"):
            store.delete_state(workflow.session_id)
            st.rerun()
        return
    except Exception:
        # Not finished yet, continue loop
        pass

    # 3. Core Loop: Process Current Turn
    # If we don't have active fields, we need to run the planner
    state = workflow.get_state()
    
    if not state.active_fields:
        with st.spinner("🔄 Planning next step..."):
            time.sleep(0.5) # Simulate network/inference lag
            workflow.step()
            st.rerun()

    # 4. Render Active Fields
    st.subheader("Please fill in the following details:")
    
    # answers is a dict if form submitted, else None
    answers = adapter.render_step(
        fields=state.active_fields,
        current_answers=state.captured_data,
        form_key="intake_form"
    )

    if answers:
        # 5. Submit Answers and Advance
        with st.spinner("💾 Saving and processing..."):
            workflow.submit_answers(answers)
            # workflow.submit_answers automatically clears active_fields, 
            # so next rerun will trigger a new planning turn.
            st.rerun()

    # Sidebar debug info
    with st.sidebar:
        st.write("### Workflow Debug")
        st.write(f"Session ID: `{workflow.session_id}`")
        st.write(f"Turns: `{state.turn_count}`")
        st.write("#### Current Data")
        st.json(state.captured_data)
        if st.button("Reset Session"):
            store.delete_state(workflow.session_id)
            st.rerun()

if __name__ == "__main__":
    main()
