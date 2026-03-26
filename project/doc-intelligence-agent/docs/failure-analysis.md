# Document Intelligence Agent -- Failure Analysis

## Known failure surfaces

### Retrieval failures
- **Semantic gap**: Query uses different terminology than the source document.
- **Chunk boundary**: The answer spans two chunks and neither chunk alone is sufficient.
- **Low relevance corpus**: The indexed documents simply do not contain the answer.

### Reasoning failures
- **Hallucination despite grounding**: Model ignores the evidence and answers from training knowledge.
- **Citation fabrication**: Model produces [Source: filename] notation but cites a file that does not contain the claimed information.
- **Over-confidence**: Model answers confidently when the evidence is weak or ambiguous.

### Tool failures
- **Argument hallucination**: Model passes arguments that do not match the tool schema.
- **Unnecessary tool calls**: Model calls tools when it already has sufficient evidence.
- **Tool error cascade**: One tool failure causes the agent to retry the same failing call.

### System failures
- **Budget exhaustion**: Complex queries require more steps than the iteration budget allows.
- **Context overflow**: Too many retrieved chunks exceed the model's context window.
- **API errors**: Model provider returns transient errors (rate limits, timeouts).

## Mitigation strategies

| Failure | Mitigation | Implemented? |
|---------|-----------|--------------|
| Semantic gap | Query expansion, multiple retrieval passes | Partial (Ch3 agent can refine) |
| Chunk boundary | Overlapping chunks | Yes (Ch2 chunker) |
| Hallucination | Grounding instruction in system prompt | Yes (Ch2 context) |
| Over-confidence | Confidence estimation + escalation | Yes (Ch3 agent) |
| Argument hallucination | Schema validation in registry | Yes (Ch2 registry) |
| Budget exhaustion | Graceful degradation with partial answer | Yes (Ch3 agent) |
| API errors | Retry with exponential backoff | Yes (Ch4 reliability) |
| Tool error cascade | Idempotency tracking | Yes (Ch4 reliability) |
