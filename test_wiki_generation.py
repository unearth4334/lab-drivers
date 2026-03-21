#!/usr/bin/env python3
"""
Helper script to test wiki documentation generation locally.
Simulates what the GitHub Actions workflow does without needing git push.

Usage: python3 test_wiki_generation.py
"""

import os
import re
import shutil
import tempfile
from pathlib import Path


def build_mkdocs():
    """Build the mkdocs documentation."""
    print("Building MkDocs documentation...")
    result = os.system("mkdocs build")
    if result != 0:
        print("❌ MkDocs build failed")
        return False
    print("✅ MkDocs build successful")
    return True


def create_wiki_structure():
    """Create a simulated wiki structure from the built site."""
    site_dir = Path("site")
    wiki_dir = Path("test_wiki_output")
    
    if wiki_dir.exists():
        shutil.rmtree(wiki_dir)
    wiki_dir.mkdir()
    
    print(f"\nGenerating wiki structure in {wiki_dir}...")
    
    # Copy the built site as-is for direct reference
    # In a real wiki, you'd want to convert HTML to Markdown
    shutil.copytree(site_dir, wiki_dir / "reference-docs", dirs_exist_ok=True)
    
    # Create an index file that explains the structure
    index_content = """# Lab Drivers Documentation Hub

This is the auto-generated documentation for lab-drivers.

## Quick Links

- **[Device Drivers](Device-Drivers)** - API reference for all supported instruments
  - [Serial Drivers](Serial-Devices)
  - [VISA Devices](VISA-Devices)
- **[Getting Started](Getting-Started)** - Installation and basic usage patterns
- **[Architecture](Architecture)** - Design principles and extension guide
- **[Examples](Examples)** - Practical code snippets and common workflows

## Directory Structure

The generated documentation is available in:
- `reference-docs/` - Full MkDocs-generated HTML reference (can be viewed locally)
- Individual `.md` files below for Wiki preview

### Important Notes

⚠️ **This is an experimental setup!** 

The auto-generation approach has some limitations:
- GitHub Wiki doesn't natively support mkdocstrings plugin
- HTML documentation can be embedded but isn't ideal for Wiki editing workflow
- Consider using GitHub Pages instead for full mkdocstrings functionality

### Alternative Recommendations

1. **GitHub Pages (Recommended)**: 
   - Deploy MkDocs to GitHub Pages for full functionality
   - Automatic preview with every commit
   - All plugins work as designed

2. **GitHub Wiki (Current Exploration)**:
   - Easier collaborative editing
   - Simpler for contributors to edit directly
   - Trade-off: loses auto-generated API docs from docstrings

3. **Hybrid Approach**:
   - Use Wiki for narrative guides and quickstarts
   - Link to GitHub Pages for complete API reference
"""
    
    with open(wiki_dir / "Home.md", "w") as f:
        f.write(index_content)
    
    print(f"✅ Wiki structure created in {wiki_dir}")
    print(f"\n📋 Contents:")
    for item in sorted(wiki_dir.iterdir()):
        if item.is_file():
            print(f"  - {item.name}")
        else:
            file_count = len(list(item.rglob("*")))
            print(f"  - {item.name}/ ({file_count} items)")
    
    return wiki_dir


def analyze_compatibility():
    """Analyze the compatibility of the current setup with Wiki auto-generation."""
    print("\n" + "="*60)
    print("WIKI AUTO-GENERATION ANALYSIS")
    print("="*60)
    
    analysis = {
        "✅ Works Great": [
            "Narrative pages (Getting Started, Install, Architecture)",
            "Basic API reference structure",
            "Automated builds on every commit",
        ],
        "⚠️ Partial Support": [
            "mkdocstrings plugin - converts to static pages but loses interactivity",
            "MkDocs plugins - search, taxonomies won't work in Wiki",
            "Material theme styling - limited CSS support in Wiki",
        ],
        "❌ Doesn't Work": [
            "Real-time API docs auto-generation from docstrings in Wiki",
            "MkDocs live search functionality",
            "Material theme dynamic features",
            "Code syntax highlighting (unless using GitHub-flavored markdown)",
        ],
    }
    
    for category, items in analysis.items():
        print(f"\n{category}")
        for item in items:
            print(f"  {item}")
    
    print("\n" + "="*60)
    print("RECOMMENDATION: Use GitHub Pages for full functionality")
    print("Setup: Settings → Pages → Deploy from branch: main, folder: /site")
    print("="*60)


if __name__ == "__main__":
    print("🚀 Testing Wiki Documentation Generation Locally\n")
    
    # Build mkdocs
    if not build_mkdocs():
        exit(1)
    
    # Create wiki structure
    wiki_output = create_wiki_structure()
    
    # Analyze compatibility
    analyze_compatibility()
    
    print("\n✨ Test complete! Check 'test_wiki_output/' directory for preview")
    print("   This simulates what would be pushed to the GitHub Wiki")
