// Template (structure) ids are "<prefix>:<category>:<name>". Most prefixes
// are the topic itself ("limit:", "integral:"); the registry topics use a
// short prefix instead.
const PREFIX_TOPIC: Record<string, string> = {
  deriv: "derivatives",
  ode: "differential_equations",
};

// The question type a registry topic's templates generate.
const TOPIC_QUESTION_TYPE: Record<string, string> = {
  limit: "limit",
  derivatives: "compute_derivative",
  differential_equations: "solve_ode",
};

/** The topic a template id belongs to (ids with no prefix are limits). */
export function templateTopic(templateId: string): string {
  const prefix = templateId.includes(":") ? templateId.split(":")[0] : "limit";
  return PREFIX_TOPIC[prefix] ?? prefix;
}

/** The question type to request for a template of `topic`. */
export function templateQuestionType(topic: string, templateId: string): string {
  if (topic === "integral") {
    return templateId.startsWith("indefinite_") || templateId.startsWith("curated_")
      ? "indefinite_integral"
      : "definite_integral";
  }
  return TOPIC_QUESTION_TYPE[topic] ?? topic;
}

/** Whether a template id comes from a registry whose cards fetch their own
 * worked variants on demand. */
export function hasStructureVariants(templateId: string): boolean {
  return ["limit:", "integral:", "deriv:", "ode:", "curated_", "int_"].some((p) => templateId.startsWith(p));
}
