# Mail Merge Application

A Streamlit application for creating personalized documents from Word templates and data sources.

## Features

- Upload Word templates with placeholders (`{{field_name}}`)
- Upload Excel/CSV data files
- Automatic field mapping between templates and data
- Preview documents before generation
- Generate multiple personalized documents
- Support for Dutch, US, and UK date formats
- Number and currency formatting
- Single document generation with web forms

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run mailMerge.py
```

## Usage

1. **Upload Template**: Upload a Word document (.docx) with placeholders like `{{Name}}` or `{{Email}}`
2. **Upload Data**: Upload an Excel or CSV file with your data
3. **Map Fields**: The app will automatically suggest field mappings
4. **Preview**: See how your documents will look
5. **Generate**: Create personalized documents for each row in your data

## Template Syntax

Use double curly braces for field placeholders:
- `{{Name}}` - Simple field
- `{{row.Name}}` - Alternative syntax
- `[OptionalField]` - Square brackets for optional fields

## Deployment Options

- **Streamlit Cloud**: Free hosting for public repositories
- **Docker**: Containerized deployment
- **Local Server**: Run on your own infrastructure
- **Cloud Platforms**: AWS, Google Cloud, Azure

## Authentication

The application supports optional authentication. To enable it:

1. Use `mailMerge_with_auth.py` instead of `mailMerge.py`
2. Set a password in Streamlit secrets or environment variables
3. Users will need to enter the password to access the application

## Contributing

This application was refactored into modular components for better maintainability:
- `template_processor.py` - Template validation and field extraction
- `data_handler.py` - Data processing and mapping logic
- `document_generator.py` - Document creation and rendering
- `ui_pages.py` - Streamlit page components
- `auth.py` - Authentication system