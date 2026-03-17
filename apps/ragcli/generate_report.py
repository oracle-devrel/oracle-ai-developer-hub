import subprocess
import os
import time

def run_command(command, description):
    print(f"Running: {description}...")
    try:
        # Run the command and capture output
        result = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True
        )
        output = result.stdout.strip()
        if result.stderr:
            output += "\n" + result.stderr.strip()
        
        # Filter out specific warnings
        lines = output.split('\n')
        filtered_lines = [line for line in lines if "WARNING: Oracle password is hardcoded" not in line]
        output = '\n'.join(filtered_lines).strip()
        
        return f"### {description}\n```bash\n$ {command}\n{output}\n```\n\n"
    except Exception as e:
        return f"### {description}\nError running command: {e}\n\n"

def main():
    report = "# ragcli End-to-End Test Report\n\n"
    
    # Create a dummy file for testing
    with open("test_document.txt", "w") as f:
        f.write("This is a test document for ragcli. It contains some sample text to verify the upload and retrieval process.")

    # 1. Help
    report += run_command("ragcli --help", "Help Command")

    # 2. Config Show (might fail if not initialized, but good to check)
    # report += run_command("ragcli config show", "Show Config") 

    # 3. Validation (Models)
    report += run_command("ragcli models list", "List Models")
    
    # 4. Initialize DB (idempotent usually)
    report += run_command("ragcli init-db", "Initialize Database")

    # 5. Status
    report += run_command("ragcli status --verbose", "System Status")

    # 6. Upload
    report += run_command("ragcli upload test_document.txt", "Upload Document")

    # 7. Query
    report += run_command('ragcli ask "What is in the test document?"', "Ask Question")

    # 8. DB Stats
    report += run_command("ragcli db stats", "Database Stats")
    
    # 9. DB Browse
    report += run_command("ragcli db browse --table DOCUMENTS --limit 5", "Browse Documents Table")

    # Cleanup
    if os.path.exists("test_document.txt"):
        os.remove("test_document.txt")

    with open("test_report_generated.md", "w") as f:
        f.write(report)

    print("Report generated at test_report_generated.md")

if __name__ == "__main__":
    main()
