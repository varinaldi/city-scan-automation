"""
Google Cloud Platform Authentication Utilities

Helper functions for checking and setting up GCP credentials
for accessing Google Cloud Storage and Earth Engine.
"""

import subprocess
from google.cloud import storage


def check_gcp_credentials():
    """
    Check if Google Cloud credentials are available

    Returns:
        bool: True if credentials work, False otherwise
    """
    try:
        # Try to create a storage client
        client = storage.Client()
        # Try to list buckets (minimal operation to test auth)
        list(client.list_buckets(max_results=1))
        print("✅ Google Cloud credentials are working!")
        return True
    except Exception as e:
        error_msg = str(e)
        print("❌ Google Cloud credentials not found or invalid\n")
        print(f"Error: {error_msg}\n")
        return False


def setup_gcp_credentials():
    """
    Guide user through credential setup

    Provides 3 options:
    1. Application Default Credentials (recommended)
    2. Service Account Key File
    3. Run auth directly from Python

    Returns:
        bool: False (always - user needs to restart after auth)
    """
    print("="*80)
    print("GOOGLE CLOUD CREDENTIALS SETUP")
    print("="*80)
    print("\nTo access GCS data, you need to authenticate with Google Cloud.\n")

    print("Option 1: Application Default Credentials (Recommended for local dev)")
    print("-" * 80)
    print("Run this in your terminal:")
    print("  gcloud auth application-default login\n")

    print("Option 2: Service Account Key File")
    print("-" * 80)
    print("Set environment variable:")
    print("  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account-key.json'\n")

    print("Option 3: Authenticate directly from this session")
    print("-" * 80)

    choice = input("\nDo you want to run 'gcloud auth application-default login' now? (y/n): ")

    if choice.lower() == 'y':
        print("\nRunning authentication...")
        try:
            result = subprocess.run(
                ['gcloud', 'auth', 'application-default', 'login'],
                capture_output=False,
                text=True
            )
            if result.returncode == 0:
                print("\n✅ Authentication successful!")
                print("   If running in Jupyter: Restart kernel (Kernel -> Restart Kernel)")
                print("   If running as script: Re-run the script")
            else:
                print("\n❌ Authentication failed. Please run manually in terminal.")
        except FileNotFoundError:
            print("\n❌ 'gcloud' command not found. Please install Google Cloud SDK:")
            print("   https://cloud.google.com/sdk/docs/install")
    else:
        print("\nPlease authenticate manually and restart this session.")

    return False


def get_gcp_project():
    """
    Get the current GCP project ID

    Returns:
        str: Project ID or None if not available
    """
    try:
        client = storage.Client()
        return client.project
    except:
        return None


def ensure_gcp_auth(auto_setup=True):
    """
    Ensure GCP credentials are available, optionally run setup if not

    Args:
        auto_setup (bool): If True, run setup wizard when creds not found

    Returns:
        bool: True if authenticated, False otherwise

    Raises:
        SystemExit: If credentials not found and auto_setup is True
    """
    if check_gcp_credentials():
        project = get_gcp_project()
        if project:
            print(f"  Project: {project}")
        return True

    if auto_setup:
        setup_gcp_credentials()
        print("\n⚠️  Cannot proceed without credentials. Please authenticate and restart.")
        raise SystemExit("Authentication required")

    return False
