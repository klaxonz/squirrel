import os
import shutil
from pathlib import Path

BATCH_SIZE = 1000
THUMBNAILS_DIR = Path(__file__).parent.parent / "static" / "thumbnails"


def get_correct_batch_name(video_id: int) -> str:
    batch_num = (video_id - 1) // BATCH_SIZE + 1
    return f"batch_{batch_num:03d}"


def reorganize_thumbnails():
    if not THUMBNAILS_DIR.exists():
        print(f"Thumbnails directory not found: {THUMBNAILS_DIR}")
        return

    files_to_move = []

    for entry in os.listdir(THUMBNAILS_DIR):
        batch_path = THUMBNAILS_DIR / entry
        if not batch_path.is_dir() or not entry.startswith("batch_"):
            continue

        for filename in os.listdir(batch_path):
            file_path = batch_path / filename
            if not file_path.is_file():
                continue

            name, ext = os.path.splitext(filename)
            if not name.isdigit():
                print(f"Skipping non-numeric filename: {filename}")
                continue

            video_id = int(name)
            correct_batch = get_correct_batch_name(video_id)

            if entry != correct_batch:
                files_to_move.append((file_path, correct_batch, filename))

    if not files_to_move:
        print("All files are in correct directories.")
        return

    print(f"Found {len(files_to_move)} files to move:")
    for src, batch, filename in files_to_move:
        print(f"  {src.parent.name}/{filename} -> {batch}/{filename}")

    confirm = input("\nProceed with moving files? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    moved = 0
    for src, batch, filename in files_to_move:
        dest_dir = THUMBNAILS_DIR / batch
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / filename

        if dest.exists():
            print(f"Warning: {dest} already exists, skipping")
            continue

        shutil.move(str(src), str(dest))
        moved += 1

    print(f"\nMoved {moved} files.")

    for entry in os.listdir(THUMBNAILS_DIR):
        batch_path = THUMBNAILS_DIR / entry
        if batch_path.is_dir() and entry.startswith("batch_"):
            if not any(batch_path.iterdir()):
                batch_path.rmdir()
                print(f"Removed empty directory: {entry}")


if __name__ == "__main__":
    reorganize_thumbnails()
