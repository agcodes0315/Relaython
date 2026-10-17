\# Relay - Judge Demo Script



\## Target Length



3-4 minutes.



\## Opening



Alexa+ can understand what a user wants.



The harder problem is preserving what the user meant after the conversation ends.



Relay is a durable execution layer for agentic tasks. It preserves constraints, approval state and execution history outside conversational memory so tasks can safely survive failures, waiting and future resume.



\## 1. Durable Delegation Contract



Start with the normal Relay workflow.



Explain that Relay converts the user's request into a durable execution contract.



That contract can preserve:



\- budget

\- deadline

\- provider requirements

\- excluded dates

\- approval state

\- recovery state



Say:



> These constraints remain authoritative even if the task later recovers or resumes.



\## 2. Human Approval



Show the approval stage.



Say:



> Relay separates recommendation from authority. The assistant can propose an action, but irreversible actions require explicit human approval.



Explain that approval is context-bound.



If provider, price or other material execution context changes, previous approval cannot silently authorize the new action.



\## 3. Failure Recovery



Show or explain a provider failure.



Say:



> When the selected provider fails, Relay does not simply let the model improvise a replacement.



> It restores the original contract, revalidates alternatives against the original constraints, and invalidates stale approval when the execution context changes.



Key line:



> Recovery cannot weaken the user's original intent.



\## 4. Durable Wait and Resume



Explain the real AWS resume path:



```text

Amazon ECS Relay MCP

&#x20;       |

&#x20;       v

Amazon DynamoDB

&#x20;       |

&#x20;       v

EventBridge Scheduler

&#x20;       |

&#x20;       v

AWS Lambda

&#x20;       |

&#x20;       v

Restored task state

