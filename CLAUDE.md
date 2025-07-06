# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
```bash
# Run the main Streamlit application
streamlit run _____Home_____.py

# Run with specific port
streamlit run _____Home_____.py --server.port 8501
```

### Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Update dependencies
pip freeze > requirements.txt
```

## Project Architecture

### Application Structure
- **Main Entry Point**: `_____Home_____.py` - Central authentication and navigation hub
- **Multi-page App**: Uses Streamlit's native page routing via `pages/` directory
- **Authentication**: Google OAuth integration with role-based access control
- **Data Storage**: Google Sheets as primary database using `gspread` library
- **File Storage**: Google Drive integration for file uploads

### Key Components

#### Authentication System
- Google OAuth login using `streamlit_oauth`
- Role-based permissions: admin, semiadmin, vvip, teacher, student, ibec
- User registration workflow with admin approval
- Session state management for user info and permissions

#### Data Management
- **Google Sheets Integration**: Using `gspread` for CRUD operations
- **Main Sheet ID**: `1Bx4otXnVjpWONjlOMAecK4l-y3CAzxyNmH-O0mcQY0E`
- **Worksheets**: LoginList, board_roles, registration, IBEC, and page-specific sheets
- **Board Permissions**: Dynamic role management stored in `board_roles` sheet

#### Page-Specific Features
- **급식정보 (Meal Info)**: NEIS API integration for school meal data
- **IBEC**: File upload/download with Google Drive integration
- **시간표 (Schedule)**: Class schedule management
- **상담일지 (Counseling Log)**: Student counseling records
- **공문목록 (Official Documents)**: Document management system
- **YTdown**: YouTube video download utility using `yt_dlp`

### External APIs and Services
- **NEIS API**: Korean educational information portal for meal data
- **Google APIs**: Drive, Sheets, OAuth
- **AI Services**: Anthropic, OpenAI, Google Generative AI integrations
- **YouTube**: Video download functionality

### Security Configuration
- **Secrets Management**: `.streamlit/secrets.toml` (excluded from git)
- **Required Secrets**: 
  - `google_service_account` - Google service account credentials
  - `neis.API_KEY` - NEIS API key
  - Additional API keys for AI services

### Development Notes
- Uses Korean Unicode filenames for pages (🌏IBEC.py, 🍔급식정보.py, etc.)
- Timezone handling with `pytz` for Seoul timezone
- File upload safety with Korean filename handling
- Error handling for API failures and permission checks