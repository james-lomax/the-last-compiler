**Question**: How should the structure of the log_branches be maintained when a divergence happens in the middle of a message sequence?
  **Assumption**: We'll compare messages sequentially and branch at the first point of divergence, keeping the common prefix in the parent branch.

**Question**: What's the exact comparison method to detect message divergence?
  **Assumption**: Compare both the role (type of message) and the content of the message.

**Question**: How should we handle updating existing branches when new messages are added to an existing conversation?
  **Assumption**: We'll traverse the tree to find the matching prefix, then either append to an existing branch or create a new branch.

**Question**: What timestamp format should be used for log filenames?
  **Assumption**: Use ISO format (YYYY-MM-DD_HH-MM-SS) for readability and proper file sorting.

**Question**: What should happen if save_logs() is called without any logs having been created?
  **Assumption**: Create an empty log file with the current timestamp.

**Question**: In the test case, there seems to be inconsistency in the nested structure. What's the expected structure?
  **Assumption**: The branch structure should contain the divergent message, not just "Hello" as shown in the test example.