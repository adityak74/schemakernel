import pytest
from streamlit.testing.v1 import AppTest
from schemakernel.models import FieldDefinition, FieldType

def test_form_adapter_rendering():
    # Setup a mini app that uses the adapter
    script = """
import streamlit as st
from schemakernel.models import FieldDefinition, FieldType
from schemakernel.adapters.streamlit import StreamlitFormAdapter
from datetime import date

adapter = StreamlitFormAdapter()
fields = [
    FieldDefinition(key="name", type=FieldType.TEXT, label="Full Name"),
    FieldDefinition(key="age", type=FieldType.INTEGER, label="Age", default=25),
    FieldDefinition(key="newsletter", type=FieldType.BOOLEAN, label="Subscribe?", default=True),
    FieldDefinition(key="role", type=FieldType.SELECT, label="Role", options=["Admin", "User", "Guest"]),
    FieldDefinition(key="interests", type=FieldType.MULTISELECT, label="Interests", options=["Python", "Streamlit", "AI"]),
    FieldDefinition(key="bio", type=FieldType.TEXTAREA, label="Bio"),
    FieldDefinition(key="dob", type=FieldType.DATE, label="Date of Birth"),
]
answers = adapter.render_step(fields, current_answers={})
if answers:
    st.markdown(f"RESULT:{answers}")
"""
    at = AppTest.from_string(script).run()
    
    # Check widgets exist and have correct defaults
    assert at.text_input(key="name").label == "Full Name"
    assert at.number_input(key="age").value == 25
    assert at.checkbox(key="newsletter").value is True
    assert at.selectbox(key="role").options == ["Admin", "User", "Guest"]
    assert at.multiselect(key="interests").options == ["Python", "Streamlit", "AI"]
    assert at.text_area(key="bio").label == "Bio"
    assert at.date_input(key="dob").label == "Date of Birth"
    
    # Simulate submission
    at.text_input(key="name").set_value("John Doe")
    at.number_input(key="age").set_value(30)
    at.selectbox(key="role").select("User")
    at.multiselect(key="interests").select("Python").select("AI")
    at.text_area(key="bio").set_value("Hello world")
    
    from datetime import date
    at.date_input(key="dob").set_value(date(1990, 1, 1))
    
    # Submit the form
    at.button[0].click().run()
    
    # Find result
    result_text = next(t.value for t in at.markdown if t.value.startswith("RESULT:"))
    assert "John Doe" in result_text
    assert "'age': 30" in result_text
    assert "'newsletter': True" in result_text
    assert "'role': 'User'" in result_text
    assert "'interests': ['Python', 'AI']" in result_text
    assert "'bio': 'Hello world'" in result_text
    assert "'dob': datetime.date(1990, 1, 1)" in result_text

def test_form_adapter_prepopulation():
    script = """
import streamlit as st
from schemakernel.models import FieldDefinition, FieldType
from schemakernel.adapters.streamlit import StreamlitFormAdapter

adapter = StreamlitFormAdapter()
fields = [
    FieldDefinition(key="name", type=FieldType.TEXT, label="Full Name"),
]
# Pre-populate with existing answers
answers = adapter.render_step(fields, current_answers={"name": "Jane Smith"})
"""
    at = AppTest.from_string(script).run()
    assert at.text_input(key="name").value == "Jane Smith"
