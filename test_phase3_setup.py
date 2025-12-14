"""
Test Phase 3 setup - verify marker-pdf and docling installations.
"""

def test_marker_imports():
    """Test that marker-pdf can be imported."""
    try:
        import marker
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        print("✓ marker-pdf imports successful")
        return True
    except ImportError as e:
        print(f"✗ marker-pdf import failed: {e}")
        return False


def test_docling_imports():
    """Test that docling can be imported."""
    try:
        import docling
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        print("✓ docling imports successful")
        return True
    except ImportError as e:
        print(f"✗ docling import failed: {e}")
        return False


def test_docling_basic():
    """Test basic docling functionality."""
    try:
        from docling.document_converter import DocumentConverter

        # Just test initialization
        converter = DocumentConverter()
        print("✓ docling DocumentConverter initialized")
        return True
    except Exception as e:
        print(f"✗ docling basic test failed: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Phase 3 Setup Tests")
    print("="*60 + "\n")

    results = []

    print("1. Testing marker-pdf imports...")
    results.append(test_marker_imports())

    print("\n2. Testing docling imports...")
    results.append(test_docling_imports())

    print("\n3. Testing docling basic functionality...")
    results.append(test_docling_basic())

    print("\n" + "="*60)
    if all(results):
        print("✓ All Phase 3 setup tests passed!")
    else:
        print(f"✗ {sum(results)}/{len(results)} tests passed")
    print("="*60)

    exit(0 if all(results) else 1)
