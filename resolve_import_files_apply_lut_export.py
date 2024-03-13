#!/usr/bin/env python
import DaVinciResolveScript as dvr_script
from datetime import datetime
from pathlib import Path
import sys, time

def get_project(pm):
    while True:
        user_input = input("What is the name of the project? ")
        project = pm.LoadProject(user_input)
        if project is None:
            while True:
                answer = input("That project doesn't exist. Would you like to create and load it? (y/n): ")
                if answer.lower() in ["y", "yes"]:
                    project = pm.CreateProject(user_input)
                    return project
                elif answer.lower() in ["n", "no"]:
                    print("Please enter a new name for the project.")
                    break
                else:
                    print("Please answer with y/n.")
        else:
            return project

def get_media_directory() -> Path:
    while True:
        user_input = input("Please enter the filepath for your media files: ")
        path = Path(user_input).expanduser()
        if not path.exists():
            print("Not a valid path, please try again.")
            continue
        return path


media_file_path = get_media_directory()
lut_name = r"Film Looks/DCI-P3 Fujifilm 3513DI D55.cube"
export_directory = media_file_path / "resolve_exports"
export_directory.mkdir(parents=True, exist_ok=True)

# Initialize the Resolve object
rslv = dvr_script.scriptapp("Resolve")

# Get the project manager and open the project
proj_mngr = rslv.GetProjectManager()
proj = get_project(proj_mngr)

# Ensure the project loaded correctly
if not proj:
    print("Failed to load the project")
    sys.exit()

# Get the media pool
media_pool = proj.GetMediaPool()
media_storage = rslv.GetMediaStorage()

# Format today's date
today = datetime.now().strftime("%Y-%m-%d")  # Format: YYYY-MM-DD

# Check for existing folders and create a new one if necessary
root_folder = media_pool.GetRootFolder()
sub_folders_list = root_folder.GetSubFolderList()

# Initialize folder name with today's date
new_folder_name = today
folder_exists = any(folder.GetName() == new_folder_name for folder in sub_folders_list)

# Increment folder name if it already exists
counter = 2
while folder_exists:
    new_folder_name = f"{today}_{counter}"
    folder_exists = any(folder.GetName() == new_folder_name for folder in sub_folders_list)
    counter += 1

# Create the new folder
new_dated_folder = media_pool.AddSubFolder(root_folder, new_folder_name)
new_source_media_folder = media_pool.AddSubFolder(new_dated_folder, "source_media")
new_timeline_folder = media_pool.AddSubFolder(new_dated_folder, "timeline")

# Ensure the folder was created successfully
if not new_dated_folder or not new_source_media_folder or not new_timeline_folder:
    print(f"Failed to create folder {new_folder_name}")
    sys.exit()

# List of file paths for movie clips
movie_clips = [file_path for file_path in media_file_path.iterdir() if file_path.is_file()]

# Import clips to the new folder in the media pool
media_pool.SetCurrentFolder(new_source_media_folder)
media_storage.AddItemListToMediaPool([str(movie_clip) for movie_clip in movie_clips])

# Set current folder to the new timeline folder
media_pool.SetCurrentFolder(new_timeline_folder)

# Create a new timeline
timeline_name = f"{new_folder_name}_timeline"
current_timeline = media_pool.CreateEmptyTimeline(timeline_name)

# Ensure the timeline was created successfully
if not current_timeline:
    print(f"Failed to create the timeline {timeline_name}")

clip_ids_list = new_source_media_folder.GetClipList()
media_pool.AppendToTimeline(clip_ids_list)

# Apply LUT to each clip
rslv.OpenPage("color")
timeline_track_index = 1

for index in range(len(current_timeline.GetItemListInTrack("video", timeline_track_index))):
    # Get the clip from the track
    clip = current_timeline.GetItemListInTrack("video", timeline_track_index)[index]

    # Apply the LUT to the clip
    clip.SetLUT(1, lut_name)

rslv.OpenPage("deliver") 

# Export settings (modify as needed)
export_settings = {
    "TargetDir": str(export_directory),
    "CustomName": "exported_clip_",
    "SelectAllFrames": True,
    "ExportVideo": True,
    "ExportAudio": True,
    "FormatWidth": 1920,
    "FormatHeight": 1080,
    "FrameRate": 23.976,
    "VideoQuality": 1,
    "AudioCodec": "Linear PCM",
    "ColorSpaceTag": "Same as Project",
    "GammaTag": "Same as Project"
}

# Export each clip individually
export_settings["CustomName"] = "%{Reel Name}_Resolve" # Update name for each clip
proj.SetSetting("Add source frame count to filename", False)
proj.SetSetting()
proj.SetCurrentRenderMode(0)
proj.SetCurrentRenderFormatAndCodec("Quicktime", "H.264")
proj.SetRenderSettings(export_settings)
proj.DeleteAllRenderJobs()

# Proceed with export?
while True:
    user_input = input("Would you like to proceed with export? (y/n): ")
    if user_input.lower() in ["y", "yes"]:
        print("Script is moving on to export the clips. Standby")
        break
    elif user_input.lower() in ["n", "no"]:
        print("Script has stopped executing prior to exporting clips")
        sys.exit()
    else:
        print(f"{user_input} is not a valid entry. Please enter y/n.")


proj.AddRenderJob()
proj.StartRendering()

# Check rendering status (basic version)
import time
while proj.IsRenderingInProgress():
    time.sleep(1) # Check every second
print("Export completed!")
