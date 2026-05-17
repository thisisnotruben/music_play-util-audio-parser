import os
import mutagen
import csv
import json
from dotenv import load_dotenv 
import tarfile
from mutagen.easyid3 import EasyID3
from pathlib import Path


class Main:

    # scan dirs
    # extract metadata to csv tables
    # extract file img cover to tarfile

    def __init__(self, scan_dir: str, dest_song_csv_path: str, dest_artist_csv_path: str, dest_album_json_path: str, dest_tar_path: str):
        self.scan_dir = scan_dir
        self.dest_song_csv_path = dest_song_csv_path
        self.dest_artist_csv_path = dest_artist_csv_path
        self.dest_album_json_path = dest_album_json_path
        self.dest_tar_path = dest_tar_path
        self.csv_headers = ['name', 'artistName', 'album', 'genre', 'length', 'audioPath', 'coverPath']

    def run(self):

        csv_file_data: list[list] = [self.csv_headers]
        cover_path_files: list[str] = []

        for (dirpath, _, filenames) in os.walk(self.scan_dir):

            for file_name in filenames:
                full_path = os.path.join(dirpath, file_name)
                audio_metadata = self.get_metadata(full_path)

                if len(audio_metadata[self.csv_headers.index('name')]) > 0 \
                and len(audio_metadata[self.csv_headers.index('artistName')]) > 0 \
                and len(audio_metadata[self.csv_headers.index('album')]) > 0:
                    csv_file_data.append(audio_metadata)

        with open(self.dest_song_csv_path, 'w') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(csv_file_data)

        header = 'artistName'
        artist_csv_data = set()
        for i in range(1, len(csv_file_data)):
            artist_csv_data.add(csv_file_data[i][self.csv_headers.index(header)])

        artist_csv_data = sorted(list(artist_csv_data))
        artist_csv_data.insert(0, header)
        artist_csv_data = [[v] for v in artist_csv_data]

        with open(self.dest_artist_csv_path, 'w') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(artist_csv_data)

        album_data = {}
        for i in range(1, len(csv_file_data)):
            album_name = csv_file_data[i][self.csv_headers.index('album')]
            song_name = csv_file_data[i][self.csv_headers.index('name')]

            if album_name in album_data.keys():
                album_data[album_name]['songs'].append(song_name)
            else:
                album_data[album_name] = {
                    'artistName': csv_file_data[i][self.csv_headers.index('artistName')],
                    'songs': [song_name],
                }
        album_data = {'values': album_data}

        with open(self.dest_album_json_path, 'w',) as f:
            f.write(json.dumps(album_data, indent='\t'))

        with tarfile.open(self.dest_tar_path, 'w:tar') as tar_file:
            for cover_path in cover_path_files:
                tar_file.add(cover_path)

    def get_metadata(self, file_path: str) -> list:
        metadata = ['' for _ in range(len(self.csv_headers))]
        metadata[self.csv_headers.index('length')] = 0

        try:
            audio = EasyID3(file_path)
            keys = audio.keys()
            for key in keys:
                match key:
                    case 'title':
                        metadata[self.csv_headers.index('name')] = audio[key][0]
                    case 'artist' | 'albumartist':
                        index = self.csv_headers.index('artistName')
                        if len(metadata[index]) == 0:
                            metadata[index] = audio[key][0]
                    case 'album' | 'genre':
                        metadata[self.csv_headers.index(key)] = audio[key][0]
                    case 'length':
                        metadata[self.csv_headers.index(key)] = int(audio[key][0])

            file_path = os.path.join(*list(Path(file_path).parts[5:]))
            metadata[self.csv_headers.index('audioPath')] = file_path

        except mutagen.MutagenError:
            pass
        finally:
            return metadata


if __name__ == "__main__":
    load_dotenv()
    args_labels = ['SCAN_DIR', 'DEST_SONG_CSV_PATH', 'DEST_ARTIST_CSV_PATH', 'DEST_ALBUM_JSON_PATH', 'DEST_TAR_PATH']
    args = [os.getenv(label) for label in args_labels]

    Main(*args).run()
