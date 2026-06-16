import re



from strategies.base import Problem, Trace, TraceStep

from strategies.program_of_thought.prompts import (

    POT_EXECUTION_OBSERVATION_TEMPLATE,

    POT_PARSE_RETRY_USER_TEMPLATE,

    POT_RETRY_USER_TEMPLATE,

    POT_SYSTEM_PROMPT,

    POT_USER_TEMPLATE,

)

from strategies.utils import (

    SOLVER_MODEL,

    append_trace_step,

    call_llm,

    extract_python_code,

    log_final_answer,

    log_phase,

    log_run_header,

    log_step,

    normalize_numeric_answer,

    run_python_code,

    trace_session,

)



MAX_RETRIES = 2



_REASONING_RE = re.compile(

    r"Reasoning:\s*(.+?)(?=```|\Z)", re.IGNORECASE | re.DOTALL

)




def _extract_reasoning(text: str) -> str:

    match = _REASONING_RE.search(text)

    return match.group(1).strip() if match else ""





def _extract_code(text: str) -> str:

    return extract_python_code(text)





def _is_gradable(stdout: str) -> bool:

    return bool(normalize_numeric_answer(stdout))





class ProgramOfThoughtStrategy:

    """Generate Python, execute in sandbox, grade from stdout (Program-of-Thought)."""



    name = "program_of_thought"



    async def solve(self, problem: Problem) -> Trace:

        trace = Trace(strategy=self.name, problem_id=problem.id)

        log_run_header(

            strategy=self.name,

            problem_id=problem.id,

            question=problem.question,

        )

        async with trace_session(self.name, problem.id, problem.question) as trace_id:

            trace.trace_id = trace_id

            final_answer = await self._run(trace, problem)

        trace.answer = log_final_answer(final_answer)

        return trace



    async def _run(self, trace: Trace, problem: Problem) -> str:

        log_phase("Program generation")

        messages: list[dict[str, str]] = [

            {"role": "system", "content": POT_SYSTEM_PROMPT},

            {

                "role": "user",

                "content": POT_USER_TEMPLATE.format(question=problem.question),

            },

        ]



        final_answer = ""

        code = ""

        raw_response = ""



        for attempt in range(1, MAX_RETRIES + 2):

            result = await call_llm(

                messages,

                model=SOLVER_MODEL,

                temperature=0.2 if attempt == 1 else 0.1,

                role="solver",

            )

            raw_response = result.content

            reasoning = _extract_reasoning(raw_response)

            code = _extract_code(raw_response)



            if reasoning:

                log_step(attempt, "reasoning", reasoning)

                append_trace_step(

                    trace,

                    TraceStep(step_type="thought", content=reasoning, data={"attempt": attempt}),

                )

            if code:

                log_step(attempt, "code", code)

            append_trace_step(

                trace,

                TraceStep(

                    step_type="code",

                    content=code or raw_response,

                    data={"attempt": attempt},

                ),

            )



            if not code:

                error = "No ```python``` code block found in the response."

                log_step(attempt, "observation", error)

                append_trace_step(

                    trace,

                    TraceStep(step_type="observation", content=error, data={"attempt": attempt}),

                )

                if attempt > MAX_RETRIES:

                    break

                messages.append({"role": "assistant", "content": raw_response})

                messages.append(

                    {

                        "role": "user",

                        "content": POT_RETRY_USER_TEMPLATE.format(

                            question=problem.question,

                            previous_code="",

                            error=error,

                        ),

                    }

                )

                continue



            log_phase("Execution")

            try:

                stdout = run_python_code(code)

                log_step(attempt, "stdout", stdout)

                append_trace_step(

                    trace,

                    TraceStep(

                        step_type="observation",

                        content=POT_EXECUTION_OBSERVATION_TEMPLATE.format(stdout=stdout),

                        data={"attempt": attempt, "success": True},

                    ),

                )

            except Exception as e:

                error = str(e).strip()

                log_step(attempt, "error", error)

                append_trace_step(

                    trace,

                    TraceStep(

                        step_type="observation",

                        content=f"Execution error: {error}",

                        data={"attempt": attempt, "success": False},

                    ),

                )

                if attempt > MAX_RETRIES:

                    break

                messages.append({"role": "assistant", "content": raw_response})

                messages.append(

                    {

                        "role": "user",

                        "content": POT_RETRY_USER_TEMPLATE.format(

                            question=problem.question,

                            previous_code=code,

                            error=error,

                        ),

                    }

                )

                continue



            if _is_gradable(stdout):

                final_answer = normalize_numeric_answer(stdout)

                append_trace_step(

                    trace,

                    TraceStep(

                        step_type="final_answer",

                        content=final_answer,

                        data={"attempt": attempt, "stdout": stdout},

                    ),

                )

                break



            if attempt > MAX_RETRIES:

                final_answer = normalize_numeric_answer(stdout)

                append_trace_step(

                    trace,

                    TraceStep(

                        step_type="final_answer",

                        content=final_answer,

                        data={"attempt": attempt, "stdout": stdout, "parsed": False},

                    ),

                )

                break



            messages.append({"role": "assistant", "content": raw_response})

            messages.append(

                {

                    "role": "user",

                    "content": POT_PARSE_RETRY_USER_TEMPLATE.format(

                        question=problem.question,

                        previous_code=code,

                        stdout=stdout or "(empty)",

                    ),

                }

            )



        if not final_answer:

            final_answer = normalize_numeric_answer(raw_response)



        return final_answer


