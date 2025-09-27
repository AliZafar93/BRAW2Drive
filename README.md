# BRAW to MP4 Converter using DaVinci Resolve

This project provides a Python script to batch convert `.braw` files to `.mp4` format using the DaVinci Resolve Python API. The script is designed to be user-friendly and can be executed from within DaVinci Resolve or externally with the appropriate setup.

## Features

- Batch conversion of `.braw` files to `.mp4`.
- Automatically skips files that have already been rendered.
- Configurable output settings including frame rate and resolution.
- Easy integration with DaVinci Resolve's scripting capabilities.

## Prerequisites

- DaVinci Resolve installed on your machine.
- Python 3.x installed.
- Access to the DaVinci Resolve Python API.

## Setup

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd braw-to-mp4-resolve
   ```

2. **Install dependencies**:
   Ensure you have the required Python packages listed in `requirements.txt`:
   ```
   pip install -r requirements.txt
   ```

3. **Configure the environment**:
   - Copy `config/.env.example` to `.env` and update the values as needed.
   - Copy `config/config.example.yaml` to `config/config.yaml` and modify the settings according to your requirements.

## Usage

### From DaVinci Resolve

1. Open DaVinci Resolve.
2. Navigate to `Workspace > Scripts > Run Script`.
3. Select `scripts/resolve_batch_braw_to_mp4.py`.
4. Provide the required command-line arguments:
   - `--src`: Source folder containing `.braw` files.
   - `--out`: Output folder for `.mp4` files.
   - `--project`: Name of the Resolve project to create or use.
   - Optional parameters: `--fps`, `--width`, `--height`, `--dry`.

### Example Command

```bash
python resolve_batch_braw_to_mp4.py --src "G:\\My Drive\\Medical Tech\\BRAW" --out "G:\\My Drive\\Medical Tech\\MP4" --project "MedicalTech_BRAW_to_MP4"
```

## Notes

- The script is best run from within DaVinci Resolve to avoid any additional setup.
- If running externally, ensure that the `PYTHONPATH` includes the Resolve's Scripting Modules folder.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.