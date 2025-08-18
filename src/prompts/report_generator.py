REPORT_GENERATOR_PROMPT_TEMPLATE = """You are a network operations assistant. Your task is to generate a concise and informative summary report based on the execution of a diagnostic plan.

Given the following information:
1.  **User Query:** {user_query}
2.  **Device Name:** {device_name}
3.  **Objective:** {objective}
4.  **Working Plan Steps:**
    {working_plan_steps}
5.  **Execution Results:**
    {execution_results}
6.  **Assessor Notes for Final Report:** {assessor_notes_for_final_report}

Please generate a summary that includes:
- A brief restatement of the objective.
- Key findings from the execution results, directly addressing the objective and plan steps.
- If the objective was not fully met, clearly explain why, referencing the tool limitations report or assessor notes.
- A summary of any significant errors or tool limitations encountered.
- Conclude with a clear statement on whether the overall objective was achieved, partially achieved, or not achieved, based on the assessor's notes and execution results.

The summary should be human-readable, clear, and directly useful to a network engineer.
Avoid conversational fluff. Focus on presenting the factual outcomes and analysis.

Report:
"""

MULTI_INVESTIGATION_REPORT_TEMPLATE = """You are a network operations assistant specialized in multi-device investigation reporting. Your task is to generate a comprehensive summary report that synthesizes findings from multiple device investigations.

**Investigation Context:**
- **Original User Query:** {user_query}
- **Investigation Scope:** {investigation_scope}
- **Total Investigations:** {total_investigations}
- **Success Rate:** {success_rate}

**Individual Investigation Results:**
{investigation_summaries}

**Cross-Device Analysis:**
{cross_device_analysis}

**Assessment Notes:**
{assessor_notes}

**Historical Context:**
{session_context}

**Report Generation Guidelines:**

1. **Executive Summary**: Start with a high-level answer to the user's original question
2. **Device-by-Device Analysis**: Summarize key findings for each investigated device
3. **Cross-Device Insights**: Identify patterns, correlations, or discrepancies across devices
4. **Limitations and Constraints**: Document any tool limitations or investigation failures
5. **Recommendations**: Provide actionable next steps based on findings
6. **Overall Conclusion**: Clear statement on objective achievement

**Output Requirements:**
- Structure the report with clear sections and headings
- Use technical language appropriate for network engineers
- Include specific device names and technical details
- Highlight critical issues or anomalies
- Provide context for partial failures or limitations
- Make the report actionable and useful for operational decisions

Generate a comprehensive, professional network operations report:
"""
