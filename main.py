import os
import mutagen
import csv
from dotenv import load_dotenv 
import tarfile
from mutagen.easyid3 import EasyID3


class Main:

    # scan dirs
    # extract metadata to csv tables
    # extract file img cover to tarfile

    def __init__(self, scan_dir: str, dest_csv_path: str, dest_tar_path: str):
        self.scan_dir = scan_dir
        self.dest_csv_path = dest_csv_path
        self.dest_tar_path = dest_tar_path
        self.csv_headers = ['name', 'artistName', 'album', 'genre', 'length', 'audioPath', 'coverPath']

    def run(self):

        csv_file_data: list[list] = [self.csv_headers]
        cover_path_files: list[str] = []

        for (dirpath, _, filenames) in os.walk(self.scan_dir):

            for file_name in filenames:
                full_path = os.path.join(dirpath, file_name)
                audio_metadata = self.get_metadata(full_path)
                if len(audio_metadata) > 0:
                    csv_file_data.append(audio_metadata)

        with open(self.dest_csv_path, 'w') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(csv_file_data)

        with tarfile.open(self.dest_tar_path, 'w:tar') as tar_file:
            for cover_path in cover_path_files:
                tar_file.add(cover_path)


    def get_metadata(self, file_path: str) -> list:
        metadata = []

        try:
            audio = EasyID3(file_path)
            keys = audio.keys()

        except mutagen.MutagenError:
            pass
        finally:
            return metadata

if __name__ == "__main__":
    load_dotenv()
    args = [os.getenv('SCAN_DIR'), os.getenv('DEST_CSV_PATH'), os.getenv('DEST_TAR_PATH')]

    Main(*args).run()
