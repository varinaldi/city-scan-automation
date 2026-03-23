def upload_blob(bucket_name, source_file_name, destination_blob_name, type = 'output', check_exists = False):
    """
    Uploads a file to the bucket.

    Args:
        bucket_name: Name of the bucket.
        source_file_name: Path to the file to upload.
        destination_blob_name: Destination name of the file in the bucket.
        type: Type of the file (output (default), render, input, data)
        check_exists: Check if the file already exists in the bucket.
    """
    import os
    from google.cloud import storage
    from os.path import exists

    if exists(source_file_name):
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        if type == 'output':
            # Mapping of file extensions to folder names
            folder_map = {
                ('.tif', '.gpkg'): 'spatial',
                ('.csv', '.txt', '.yml'): 'tabular',
                ('.png'): 'images'
            }

            # Default folder name for other file types
            default_folder = 'other'

            # Get the folder name based on file extension
            for extensions, folder_name in folder_map.items():
                if any(destination_blob_name.endswith(ext) for ext in extensions):
                    target_folder = folder_name
                    break
            else:
                target_folder = default_folder

            # Construct the new destination_blob_name
            destination_blob_name = f'{os.path.dirname(destination_blob_name)}/{target_folder}/{os.path.basename(destination_blob_name)}'
        elif type == 'render':
            # Mapping of file extensions to folder names
            folder_map = {
                ('.html'): 'plots/html',
                ('.png'): 'plots/png'
            }

            # Default folder name for other file types
            default_folder = 'other'

            # Get the folder name based on file extension
            for extensions, folder_name in folder_map.items():
                if any(destination_blob_name.endswith(ext) for ext in extensions):
                    target_folder = folder_name
                    break
            else:
                target_folder = default_folder

            # Construct the new destination_blob_name
            destination_blob_name = f'{os.path.dirname(destination_blob_name)}/{target_folder}/{os.path.basename(destination_blob_name)}'

        blob = bucket.blob(destination_blob_name)
        if check_exists:
            if blob.exists():
                print(f"File {destination_blob_name} already exists.")
                return
        blob.upload_from_filename(source_file_name)
        print(f"File {source_file_name} uploaded to {destination_blob_name}.")
        return True
    print(f"File {source_file_name} does not exist.")
    return False


def get_all_files(directory):
    """
    Get set of all files in a directory tree.
    Returns absolute paths of all files found.
    """
    import os
    
    if not os.path.exists(directory):
        return set()
    
    files = set()
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            files.add(os.path.join(root, filename))
    return files


def upload_task_outputs(scan, task_name, step=None, files_before=None):
    """
    Upload task outputs to GCS. Only uploads files that didn't exist before.
    
    Automatically constructs paths using scan.cityscan_id and scan.output_dir/render_dir.
    Example: local file 'mnt/2026-03-indonesia-south_jakarta/02-process-output/spatial/file.tif'
             uploads to 'gs://crp-city-scan/2026-03-indonesia-south_jakarta/02-process-output/spatial/file.tif'
    
    Args:
        scan: Scan object with cityscan_id and output directories
        task_name: Name of the task (e.g., 'wsf', 'accessibility')
        step: Optional step identifier ('collect', 'analyze', 'visualize', or None for full run)
        files_before: Set of files that existed before task execution.
                     If None, uploads all current files.
    
    Returns:
        bool: True if upload succeeded or was fully attempted, False on critical error
    """
    from google.cloud import storage
    import os
    from core.py.log_module import setup_logger
    
    logger = setup_logger("gcs_upload")
    
    try:
        bucket_name = "crp-city-scan"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Get current files
        current_files = get_all_files(scan.output_dir) | get_all_files(scan.render_dir)
        
        # Determine new files
        if files_before is not None:
            new_files = current_files - files_before
        else:
            new_files = current_files
        
        if not new_files:
            step_str = f" ({step})" if step else ""
            logger.info(f"Task '{task_name}'{step_str}: No new files to upload")
            return True
        
        # Upload each new file
        uploaded_count = 0
        for local_path in new_files:
            try:
                # Determine relative path from parent of output_dir
                if local_path.startswith(str(scan.output_dir)):
                    relative_path = os.path.relpath(local_path, os.path.dirname(scan.output_dir))
                elif local_path.startswith(str(scan.render_dir)):
                    relative_path = os.path.relpath(local_path, os.path.dirname(scan.render_dir))
                else:
                    logger.warning(f"File {local_path} not in expected directories, skipping")
                    continue
                
                # Construct GCS path: cityscan_id/02-process-output/...
                gcs_path = f"{scan.cityscan_id}/{relative_path}"
                
                # Upload to GCS
                blob = bucket.blob(gcs_path)
                blob.upload_from_filename(local_path)
                logger.info(f"Uploaded: gs://{bucket_name}/{gcs_path}")
                uploaded_count += 1
                
            except Exception as e:
                logger.error(f"Failed to upload {local_path}: {e}")
                continue
        
        step_str = f" ({step})" if step else ""
        logger.info(f"Task '{task_name}'{step_str}: Uploaded {uploaded_count} files to gs://{bucket_name}/{scan.cityscan_id}/")
        return True
        
    except Exception as e:
        logger.error(f"Critical error uploading outputs for task '{task_name}': {e}")
        return False