import unittest
from unittest.mock import MagicMock
import sys

# Mock standard library modules that require a display
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()

# Mock customtkinter
ctk_mock = MagicMock()
sys.modules['customtkinter'] = ctk_mock

# Now import the app (which uses the mocks)
import annotate_and_merge

class TestPDFAnnotatorApp(unittest.TestCase):
    def test_app_instantiation(self):
        """Test that the app class instantiates without error."""
        try:
            app = annotate_and_merge.PDFAnnotatorApp()
            print("App instantiated successfully.")
            # Verify that we set the title and geometry (just to check some side effects)
            # Since the base class is a Mock, these methods should have been called on the instance (which is also somewhat mock-like in behavior regarding super calls)
            # Actually, since it inherits from MagicMock, self.title(...) calls MagicMock.title(...)

        except Exception as e:
            self.fail(f"App instantiation failed with error: {e}")

if __name__ == '__main__':
    unittest.main()
