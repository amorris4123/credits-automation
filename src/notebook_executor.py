"""
Notebook Executor
Executes Jupyter notebooks with papermill and extracts results
"""

import papermill as pm
import nbformat
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from .config import Config

logger = logging.getLogger(__name__)


class NotebookExecutor:
    """Executor for running Jupyter notebooks with parameters"""

    def __init__(self, notebook_path: Path = None, output_dir: Path = None):
        """
        Initialize notebook executor

        Args:
            notebook_path: Path to notebook file (defaults to Config)
            output_dir: Directory for output notebooks (defaults to Config)
        """
        self.notebook_path = notebook_path or Config.NOTEBOOK_PATH
        self.output_dir = output_dir or Config.OUTPUT_DIR

        # Verify notebook exists
        if not self.notebook_path.exists():
            raise FileNotFoundError(f"Notebook not found: {self.notebook_path}")

        logger.info(f"Notebook executor initialized with: {self.notebook_path}")

    def execute(self, looker_query: str, asid: str = None) -> Dict[str, Any]:
        """
        Execute notebook with SQL query parameter

        Args:
            looker_query: SQL query to pass to notebook
            asid: Account SID for tracking (optional)

        Returns:
            Dict with execution results:
            {
                'success': True/False,
                'credit_amount': float or None,
                'output_path': Path to output notebook,
                'error': error message if failed,
                'execution_time': seconds
            }
        """
        start_time = datetime.now()

        # Generate output filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        asid_str = f"_{asid}" if asid else ""
        output_filename = f"output_{timestamp}{asid_str}.ipynb"
        output_path = self.output_dir / output_filename

        logger.info(f"Executing notebook with parameters")
        logger.info(f"Output will be saved to: {output_path}")

        try:
            # Execute notebook with papermill
            # The notebook expects a parameter called 'looker' (not 'sql_query')
            pm.execute_notebook(
                input_path=str(self.notebook_path),
                output_path=str(output_path),
                parameters={
                    'looker': looker_query  # Parameter name from interview answers
                },
                kernel_name='python3'  # Adjust if using different kernel
            )

            # Extract credit_amount from output notebook
            credit_amount = self._extract_credit_amount(output_path)

            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Notebook executed successfully in {execution_time:.2f}s")
            logger.info(f"Credit amount: ${credit_amount}" if credit_amount else "No credit amount found")

            return {
                'success': True,
                'credit_amount': credit_amount,
                'output_path': output_path,
                'error': None,
                'execution_time': execution_time
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Notebook execution failed after {execution_time:.2f}s: {e}")

            return {
                'success': False,
                'credit_amount': None,
                'output_path': output_path if output_path.exists() else None,
                'error': str(e),
                'execution_time': execution_time
            }

    def _extract_credit_amount(self, notebook_path: Path) -> Optional[float]:
        """
        Extract credit_amount variable from executed notebook

        Args:
            notebook_path: Path to executed notebook

        Returns:
            credit_amount value if found, None otherwise
        """
        try:
            # Read the executed notebook
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)

            # Search through cells for credit_amount variable
            for cell in nb.cells:
                if cell.cell_type == 'code':
                    # Check cell outputs
                    outputs = cell.get('outputs', [])
                    for output in outputs:
                        # Check display_data and execute_result
                        if output.get('output_type') in ['display_data', 'execute_result']:
                            data = output.get('data', {})
                            text = data.get('text/plain', '')

                            # Look for credit_amount in the output
                            if 'credit_amount' in cell.get('source', ''):
                                # Try to parse the value
                                try:
                                    # Remove quotes and parse as float
                                    value_str = text.strip().strip("'\"")
                                    credit_amount = float(value_str)
                                    return credit_amount
                                except (ValueError, AttributeError):
                                    pass

                    # Also check if the cell explicitly assigns credit_amount
                    source = cell.get('source', '')
                    if 'credit_amount =' in source or 'credit_amount=' in source:
                        # Try to find the value in outputs
                        for output in outputs:
                            if output.get('output_type') == 'stream':
                                text = output.get('text', '')
                                # Try to parse any number from the output
                                import re
                                numbers = re.findall(r'\$?(\d+\.?\d*)', text)
                                if numbers:
                                    try:
                                        return float(numbers[0])
                                    except ValueError:
                                        pass

            # If not found in outputs, try to find in the last cell
            # Sometimes the final value is just displayed without explicit output
            if nb.cells:
                last_cell = nb.cells[-1]
                if last_cell.cell_type == 'code':
                    outputs = last_cell.get('outputs', [])
                    for output in outputs:
                        if output.get('output_type') in ['display_data', 'execute_result']:
                            data = output.get('data', {})
                            text = data.get('text/plain', '').strip()

                            # Try to parse as float
                            try:
                                # Handle potential $ signs and commas
                                cleaned = text.replace('$', '').replace(',', '').strip("'\"")
                                credit_amount = float(cleaned)
                                return credit_amount
                            except (ValueError, AttributeError):
                                pass

            logger.warning("Could not extract credit_amount from notebook output")
            return None

        except Exception as e:
            logger.error(f"Error extracting credit_amount: {e}")
            return None

    def is_verify_query(self, sql_query: str) -> bool:
        """
        Check if SQL query is for Verify product (contains "Authy")

        Args:
            sql_query: SQL query string

        Returns:
            True if query appears to be for Verify, False otherwise
        """
        # Check for "Authy" in the query (case-insensitive)
        if 'authy' in sql_query.lower():
            return True

        # Check for specific Verify-related table/column names
        verify_indicators = [
            'billable_item_metadata_alex.product',
            'billable_items.friendly_name',
            'verify',
            'verification'
        ]

        query_lower = sql_query.lower()
        return any(indicator in query_lower for indicator in verify_indicators)


# Example usage
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # Test with a sample query
    test_query = """
    SELECT * FROM billing
    WHERE product = 'Authy'
    LIMIT 10
    """

    executor = NotebookExecutor()

    # Test if it's a Verify query
    is_verify = executor.is_verify_query(test_query)
    print(f"Is Verify query: {is_verify}")

    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        print("\nExecuting notebook with test query...")
        result = executor.execute(test_query, asid="ACTEST123")

        print(f"\nResult:")
        print(f"  Success: {result['success']}")
        print(f"  Credit Amount: ${result['credit_amount']}")
        print(f"  Execution Time: {result['execution_time']:.2f}s")
        print(f"  Output: {result['output_path']}")
        if result['error']:
            print(f"  Error: {result['error']}")
