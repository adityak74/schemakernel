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
    WorkflowStage,
    PolicyConfig,
)
import time
from typing import Any

# --- Mock Planner Implementation ---
# A simple hardcoded planner to simulate adaptive field generation without LLM.
class MockPatientPlanner:
    def call(self, messages: list[dict], system_prompt: str) -> PlannerResponse:
        """
        Simulates an adaptive intake process.
        - First step: Ask for Name and Age.
        - Second step (if Age > 18): Ask for Occupation.
        - Second step (if Age <= 18): Ask for School and Grade.
        - Final step: Complete.
        """
        # HACK: Retrieve the session state directly for the mock.
        # In a real LLM planner, this information would be derived from the prompt.
        session_key = "sk_demo_patient-intake-session_state"
        state_obj = st.session_state.get(session_key)
        
        if not state_obj:
            # Should not happen if run_planner_turn is called, but safety first.
            return PlannerResponse(
                actions=[], rationale=["No state found."], 
                completion_status=CompletionStatus.IN_PROGRESS
            )

        data = state_obj.answers
        existing_fields = state_obj.fields

        # 1. Initial fields (Name and Age)
        if "name" not in existing_fields and "age" not in existing_fields:
            f1 = FieldDefinition(key="name", label="Full Name", type=FieldType.TEXT, required=True)
            f2 = FieldDefinition(key="age", label="Age", type=FieldType.INTEGER, required=True)
            return PlannerResponse(
                actions=[
                    PlannerAction(action=ActionType.ADD, field_key="name"),
                    PlannerAction(action=ActionType.ADD, field_key="age"),
                ],
                fields=[f1, f2],
                rationale=["Starting intake with basic demographics."],
                completion_status=CompletionStatus.IN_PROGRESS
            )

        # 2. Check if name/age are answered yet
        if "name" not in data or "age" not in data:
            return PlannerResponse(
                actions=[],
                rationale=["Waiting for name and age to be answered."],
                completion_status=CompletionStatus.IN_PROGRESS
            )

        # 3. Conditional fields based on age
        age = int(data["age"])
        if age > 18:
            if "occupation" not in existing_fields:
                f3 = FieldDefinition(key="occupation", label="Occupation", type=FieldType.TEXT)
                return PlannerResponse(
                    actions=[PlannerAction(action=ActionType.ADD, field_key="occupation")],
                    fields=[f3],
                    rationale=["User is an adult, asking for occupation."],
                    completion_status=CompletionStatus.IN_PROGRESS
                )
        else:
            if "school" not in existing_fields:
                f4 = FieldDefinition(key="school", label="School Name", type=FieldType.TEXT)
                f5 = FieldDefinition(key="grade", label="Grade", type=FieldType.INTEGER)
                return PlannerResponse(
                    actions=[
                        PlannerAction(action=ActionType.ADD, field_key="school"),
                        PlannerAction(action=ActionType.ADD, field_key="grade"),
                    ],
                    fields=[f4, f5],
                    rationale=["User is a minor, asking for school details."],
                    completion_status=CompletionStatus.IN_PROGRESS
                )

        # 4. Check if conditional fields are answered
        if age > 18 and "occupation" not in data:
            return PlannerResponse(actions=[], rationale=["Waiting for occupation."], completion_status=CompletionStatus.IN_PROGRESS)
        if age <= 18 and ("school" not in data or "grade" not in data):
            return PlannerResponse(actions=[], rationale=["Waiting for school/grade."], completion_status=CompletionStatus.IN_PROGRESS)

        # 5. Final Completion
        return PlannerResponse(
            actions=[PlannerAction(action=ActionType.COMPLETE)],
            rationale=["All information gathered."],
            completion_status=CompletionStatus.COMPLETE
        )

# --- Streamlit UI logic ---

def main():
    st.set_page_config(page_title="SchemaKernel Demo", page_icon="🏥")
    st.title("🏥 Patient Intake (SchemaKernel Demo)")
    st.markdown("""
        This demo uses `schemakernel` to manage an adaptive form flow. 
        The fields shown depend on your previous answers.
    """)

    SESSION_ID = "patient-intake-session"

    # 1. Initialize SchemaKernel Components
    store = StreamlitSessionStore(key_prefix="sk_demo_")
    adapter = StreamlitFormAdapter()
    
    # We use a default PolicyConfig (no baseline questions) 
    # to let the Mock Planner drive the whole flow.
    workflow = create_workflow(
        planner=MockPatientPlanner(),
        store=store
    )

    # 2. Load or Start Session
    try:
        state = workflow.get_state(SESSION_ID)
    except Exception:
        # Start new session if not exists
        state = workflow.start_session(SESSION_ID)

    # 3. Check if complete
    if state.stage == WorkflowStage.COMPLETE:
        st.success("✅ Intake Complete!")
        st.write("### Captured Data")
        st.json(state.answers)
        if st.button("Restart"):
            store.delete_state(SESSION_ID)
            st.rerun()
        return

    # 4. Logic: Determine if we need more fields
    # If all existing fields are answered, we call the planner to see what's next.
    unanswered = [k for k in state.field_order if k not in state.answers]
    
    if not unanswered:
        with st.spinner("🔄 Planning next step..."):
            time.sleep(0.5) # Simulate lag
            workflow.run_planner_turn(SESSION_ID)
            st.rerun()

    # 5. Render Active Fields (the unanswered ones)
    st.subheader("Please fill in the following details:")
    
    active_fields = [state.fields[k] for k in unanswered]
    
    # answers is a dict if form submitted, else None
    new_answers = adapter.render_step(
        fields=active_fields,
        current_answers=state.answers,
        form_key="intake_form"
    )

    if new_answers:
        # 6. Submit Answers and Advance
        with st.spinner("💾 Saving..."):
            for k, v in new_answers.items():
                workflow.submit_answer(SESSION_ID, k, v)
            st.rerun()

    # Sidebar debug info
    with st.sidebar:
        st.write("### Workflow Debug")
        st.write(f"Session ID: `{SESSION_ID}`")
        st.write(f"Stage: `{state.stage.value}`")
        st.write(f"Turns: `{state.turn_count}`")
        st.write("#### Current Data")
        st.json(state.answers)
        if st.button("Reset Session"):
            store.delete_state(SESSION_ID)
            st.rerun()

if __name__ == "__main__":
    main()
