# AI Agent Development Guidelines

Welcome to the NFS Resources Converter project! To ensure smooth, reproducible, and error-free development, please follow these guidelines carefully.

### Development Environment Setup

- **Python Version**: This project uses **Python 3.14**.
- **Virtual Environment**: All dependencies must be managed within a virtual environment located at `./.venv` in the project root.

### Guidelines for AI Agents

1. **Activation of Virtual Environment**:
   - If the `.venv` directory already exists, always activate it before launching any Python scripts or commands:
     - On macOS/Linux: `source .venv/bin/activate` or invoke Python explicitly using `./.venv/bin/python`
     - On Windows: `.venv\Scripts\activate` or invoke Python explicitly using `.\.venv\Scripts\python`
   
2. **Environment Initialization**:
   - If the `.venv` directory does not exist, you must create it once:
     ```bash
     python3.14 -m venv .venv
     ```
   - After creation, activate the virtual environment and install the required packages listed in `requirements.txt`:
     ```bash
     ./.venv/bin/pip install -r requirements.txt
     ```

3. **Running Code & Tests**:
   - Always run the test suite and application code through the virtual environment Python interpreter. For example:
     ```bash
     ./.venv/bin/python -m unittest
     ```
