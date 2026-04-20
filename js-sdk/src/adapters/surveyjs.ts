import {
  SchemaState,
  FieldType,
  ConditionOperator,
  ConditionalLogic,
  Condition,
  FieldDefinition,
} from "../models";

/**
 * Maps SchemaKernel FieldType to SurveyJS question type.
 */
const TYPE_MAP: Record<FieldType, string> = {
  [FieldType.TEXT]: "text",
  [FieldType.NUMBER]: "text",
  [FieldType.INTEGER]: "text",
  [FieldType.BOOLEAN]: "boolean",
  [FieldType.DATE]: "text",
  [FieldType.DATETIME]: "text",
  [FieldType.SELECT]: "dropdown",
  [FieldType.MULTISELECT]: "checkbox",
  [FieldType.EMAIL]: "text",
  [FieldType.URL]: "text",
  [FieldType.PHONE]: "text",
  [FieldType.TEXTAREA]: "comment",
};

/**
 * Maps SchemaKernel ConditionOperator to SurveyJS operator.
 */
function mapOperator(operator: ConditionOperator): string {
  switch (operator) {
    case ConditionOperator.EQ:
      return "=";
    case ConditionOperator.NEQ:
      return "<>";
    case ConditionOperator.GT:
      return ">";
    case ConditionOperator.GTE:
      return ">=";
    case ConditionOperator.LT:
      return "<";
    case ConditionOperator.LTE:
      return "<=";
    case ConditionOperator.IN:
      return "anyof";
    case ConditionOperator.NOT_IN:
      return "noneof";
    case ConditionOperator.IS_EMPTY:
      return "empty";
    case ConditionOperator.NOT_EMPTY:
      return "notempty";
    default:
      return "=";
  }
}

/**
 * Formats a value for SurveyJS expression.
 */
function formatValue(value: any): string {
  if (typeof value === "string") {
    return `'${value.replace(/'/g, "\\'")}'`;
  }
  if (Array.isArray(value)) {
    return `[${value.map(formatValue).join(", ")}]`;
  }
  return String(value);
}

/**
 * Maps a single Condition to SurveyJS expression string.
 */
function mapCondition(condition: Condition): string {
  const operator = mapOperator(condition.operator);
  const left = `{${condition.field_key}}`;

  if (condition.operator === ConditionOperator.IS_EMPTY || condition.operator === ConditionOperator.NOT_EMPTY) {
    return `${left} is ${operator}`;
  }

  const right = formatValue(condition.value);
  return `${left} ${operator} ${right}`;
}

/**
 * Maps ConditionalLogic to SurveyJS expression string.
 */
function mapConditionalLogic(logic: ConditionalLogic): string {
  const parts = logic.conditions.map(mapCondition);
  const separator = ` ${logic.combinator} `;
  return parts.join(separator);
}

/**
 * Maps a single FieldDefinition to SurveyJS element.
 */
function mapField(field: FieldDefinition): any {
  const element: any = {
    name: field.key,
    type: TYPE_MAP[field.type] || "text",
    title: field.label,
    description: field.description,
    isRequired: field.required,
    ...field.ui_props,
  };

  if (field.type === FieldType.NUMBER || field.type === FieldType.INTEGER) {
    element.inputType = "number";
  } else if (field.type === FieldType.DATE) {
    element.inputType = "date";
  } else if (field.type === FieldType.DATETIME) {
    element.inputType = "datetime-local";
  } else if (field.type === FieldType.EMAIL) {
    element.inputType = "email";
  } else if (field.type === FieldType.URL) {
    element.inputType = "url";
  } else if (field.type === FieldType.PHONE) {
    element.inputType = "tel";
  }

  if (field.options) {
    element.choices = field.options;
  }

  if (field.default !== undefined && field.default !== null) {
    element.defaultValue = field.default;
  }

  if (field.visible_if) {
    element.visibleIf = mapConditionalLogic(field.visible_if);
  }

  return element;
}

/**
 * Maps SchemaState to SurveyJS JSON structure.
 */
export function mapToSurveyJS(state: SchemaState): any {
  const elements = state.field_order.map((key) => {
    const field = state.fields[key];
    return mapField(field);
  });

  return {
    showQuestionNumbers: "off",
    elements,
  };
}
