import uuid
from task_queue.tasks import run_agent_task

task_id = str(uuid.uuid4())
prompt = "Calculate the exact Fourier series expansion for a square wave. Show all the mathematical steps beautifully formatted on the screen using LaTeX math. Attempt to plot the wave visually. Finally, package the entire mathematical derivation into a downloadable PDF."

print(f"Triggering task: {task_id}")
result = run_agent_task.run(task_id, prompt, "test_user_hash")
print("=== FINAL RESULT ===")
print(result)
