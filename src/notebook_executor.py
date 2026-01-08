"""
Notebook Executor
Executes Jupyter notebooks with papermill and extracts results
"""

import papermill as pm
import nbformat
import logging
import json
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
        temp_notebook_path = self.output_dir / f"temp_{timestamp}{asid_str}.ipynb"
        summary_json_path = self.output_dir / f"summary_{timestamp}{asid_str}.json"

        logger.info(f"Executing notebook with parameters")
        logger.info(f"Summary will be saved to: {summary_json_path}")

        try:
            # Execute notebook with papermill (temporarily save full notebook)
            # The notebook expects a parameter called 'looker' (not 'sql_query')
            pm.execute_notebook(
                input_path=str(self.notebook_path),
                output_path=str(temp_notebook_path),
                parameters={
                    'looker': looker_query  # Parameter name from interview answers
                },
                kernel_name='python3'  # Adjust if using different kernel
            )

            # Extract summary info from executed notebook
            summary_data = self._extract_summary_info(temp_notebook_path)
            credit_amount = summary_data['credit_amount']

            # Save summary as JSON
            with open(summary_json_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, default=str)

            # Delete the full notebook to save space
            if temp_notebook_path.exists():
                temp_notebook_path.unlink()
                logger.info(f"Deleted temporary full notebook: {temp_notebook_path}")

            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Notebook executed successfully in {execution_time:.2f}s")
            logger.info(f"Summary saved to: {summary_json_path}")
            logger.info(f"Credit amount: ${credit_amount}" if credit_amount else "No credit amount found")

            return {
                'success': True,
                'credit_amount': credit_amount,
                'output_path': summary_json_path,  # Now returns JSON path instead of notebook
                'error': None,
                'execution_time': execution_time
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Notebook execution failed after {execution_time:.2f}s: {e}")

            # Clean up temporary notebook if it exists
            if temp_notebook_path.exists():
                temp_notebook_path.unlink()

            return {
                'success': False,
                'credit_amount': None,
                'output_path': None,
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

    def _extract_summary_info(self, notebook_path: Path) -> Dict[str, Any]:
        """
        Extract only Summary Info section from executed notebook

        Args:
            notebook_path: Path to executed notebook

        Returns:
            Dict containing summary data and credit amount
        """
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)

            summary_data = {
                'extracted_at': datetime.now().isoformat(),
                'notebook_path': str(notebook_path),
                'summary_outputs': {},
                'credit_amount': None
            }

            # Find "Summary Info" section
            in_summary = False
            for idx, cell in enumerate(nb.cells):
                # Look for the "## Summary Info" markdown header
                if cell.cell_type == 'markdown' and 'Summary Info' in cell.get('source', ''):
                    in_summary = True
                    logger.info("Found Summary Info section in notebook")
                    continue

                # Process code cells in summary section
                if in_summary and cell.cell_type == 'code':
                    cell_source = cell.get('source', '')

                    # Extract key summary cells
                    if any(keyword in cell_source for keyword in ['output_df', 'credit_amount', 'asid_df', 'blocking']):
                        cell_id = f"cell_{idx}"

                        # Get cell outputs (text, data, etc.)
                        outputs = cell.get('outputs', [])
                        serialized_outputs = self._serialize_cell_outputs(outputs)

                        summary_data['summary_outputs'][cell_id] = {
                            'source': cell_source[:500],  # Limit source length
                            'outputs': serialized_outputs
                        }

                        # Check if this cell calculates credit_amount
                        if 'credit_amount' in cell_source and '=' in cell_source:
                            # Try to extract the credit amount value
                            credit = self._extract_credit_from_cell(cell)
                            if credit is not None:
                                summary_data['credit_amount'] = credit
                                logger.info(f"Found credit_amount in summary: ${credit:.2f}")

            # If we didn't find credit_amount in summary section, try the full notebook
            if summary_data['credit_amount'] is None:
                summary_data['credit_amount'] = self._extract_credit_amount(notebook_path)

            return summary_data

        except Exception as e:
            logger.error(f"Error extracting summary info: {e}")
            return {
                'extracted_at': datetime.now().isoformat(),
                'notebook_path': str(notebook_path),
                'summary_outputs': {},
                'credit_amount': None,
                'error': str(e)
            }

    def _serialize_cell_outputs(self, outputs: list) -> list:
        """
        Serialize cell outputs to JSON-compatible format

        Args:
            outputs: List of cell outputs from nbformat

        Returns:
            List of serialized outputs
        """
        serialized = []
        for output in outputs[:5]:  # Limit to first 5 outputs
            try:
                output_type = output.get('output_type', '')

                if output_type == 'stream':
                    # Text output (print statements)
                    text = output.get('text', '')
                    if isinstance(text, list):
                        text = ''.join(text)
                    serialized.append({
                        'type': 'stream',
                        'text': text[:1000]  # Limit length
                    })

                elif output_type in ['execute_result', 'display_data']:
                    # Data outputs (dataframes, values, etc.)
                    data = output.get('data', {})
                    text_plain = data.get('text/plain', '')
                    if isinstance(text_plain, list):
                        text_plain = ''.join(text_plain)
                    serialized.append({
                        'type': output_type,
                        'text': text_plain[:1000]  # Limit length
                    })

            except Exception as e:
                logger.warning(f"Error serializing output: {e}")
                continue

        return serialized

    def _extract_credit_from_cell(self, cell: dict) -> Optional[float]:
        """
        Extract credit amount from a specific cell's outputs

        Args:
            cell: Notebook cell dict

        Returns:
            Credit amount as float or None
        """
        try:
            outputs = cell.get('outputs', [])
            for output in outputs:
                if output.get('output_type') in ['execute_result', 'display_data']:
                    data = output.get('data', {})
                    text = data.get('text/plain', '')

                    if isinstance(text, list):
                        text = ''.join(text)

                    # Try to parse as float
                    # Handle formats like: '$4,948.80', '4948.80', etc.
                    cleaned = str(text).strip().replace('$', '').replace(',', '').replace("'", '').replace('"', '')

                    try:
                        return float(cleaned)
                    except ValueError:
                        continue

        except Exception as e:
            logger.debug(f"Could not extract credit from cell: {e}")

        return None

    def is_verify_query(self, sql_query: str) -> bool:
        """
        Check if SQL query is for Verify product (contains "Authy")

        Only looks for "authy" keyword in the context of:
        - billable_item_metadata_alex.product column
        - billable_items.friendly_name column

        Args:
            sql_query: SQL query string

        Returns:
            True if query appears to be for Verify, False otherwise (PSMS)
        """
        sql_lower = sql_query.lower()

        # Look for "authy" keyword (case insensitive)
        if 'authy' not in sql_lower:
            return False

        # Verify it's in context of product or friendly_name columns
        # This helps ensure we're detecting Verify product correctly
        has_product_column = 'billable_item_metadata_alex.product' in sql_lower
        has_friendly_name_column = 'billable_items.friendly_name' in sql_lower

        return has_product_column or has_friendly_name_column


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
