From the software engineering perspective I want the implementation to follow these principles:

- DRY (Don't Repeat Yourself): Avoid code duplication by centralizing the logic for loading environment variables in a single module. This will make the codebase cleaner and easier to maintain.
- KISS (Keep It Simple, Stupid): The solution should be straightforward and easy to understand. Avoid unnecessary complexity in the implementation.
- YAGNI (You Aren't Gonna Need It): Focus on the current requirements and avoid adding features or functionality that are not needed at this moment. The implementation should be focused on the task at hand without over-engineering.
- SOLID principles: Ensure that the code adheres to the SOLID principles of object-oriented design, promoting maintainability and scalability.
- Modularity: The code should be organized into modules that encapsulate specific functionality, making it easier to test and maintain.
- Readability: The code should be easy to read and understand, with clear naming conventions and comments where necessary.
- Zen of Python: The implementation should follow the principles outlined in the Zen of Python, such as simplicity, readability, and explicitness.
- Follow Martin Fowler's Refactoring Principles: The implementation should adhere to the refactoring principles outlined by Martin Fowler, promoting clean code and maintainability. The key is to write code that humans can understand easily.

The use of dictionaries to encapsulate related data and functionality is prohibited and is an anti-pattern. Objects must be used instead to promote better structure and organization of the code.

From the software engineering principles, readability is paramount and the most important aspect of the implementation. Then modularity and maintainability are also important, as they will help ensure that the code can be easily updated and extended in the future. The implementation should be straightforward and easy to understand, avoiding unnecessary complexity.

These are rules you must always follow:

- You must never commit any files. I used the staging directory to prepare changes before committing. If you commit a change, you mess with my workflow.
- You must never push any commits to any remote branches. I use commits to review changes before they are merged.
- You must never merge a PR. I use PRs to review changes before they are merged.
- To test the cli, use the uv run ... capture the output to a log file and inspect the log file to verify the output. The terminal output sometimes is cutoff.
- If you need to run tests, use the pytest cli rather than the integrated test terminal, from time to time the integrated test terminal hangs and does not show the output of the tests, so it is better to run pytest from the cli.
- If they find areas of opportunity to improve the codebase for this task or other tasks, ask them to add them as notes on the issue.
- If any agent encounters obstacles or challenges during their work, they should document these issues in the issue thread and seek assistance from the team.
