from __future__ import annotations

"""
gui.py

PyQt6-based GUI for the Last.fm exporter.
"""

import sys
from pathlib import Path
from typing import Optional

from PyQt6 import QtCore, QtWidgets

from lastfm_client import LastFMClient, LastFMError
from exporter import LastFMLibraryExporter, ExportResult


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Last.fm Library Exporter")

        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)

        self.api_key_edit = QtWidgets.QLineEdit()
        self.api_key_edit.setPlaceholderText("Enter your Last.fm API key")
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        self.username_edit = QtWidgets.QLineEdit()
        self.username_edit.setPlaceholderText("Enter Last.fm username")

        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit.setPlaceholderText("Choose output directory")

        self.browse_button = QtWidgets.QPushButton("Browse...")

        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItem("JSON only")
        self.format_combo.addItem("CSV only")
        self.format_combo.addItem("JSON + CSV (recommended)")
        self.format_combo.setCurrentIndex(2)

        self.base_name_edit = QtWidgets.QLineEdit("lastfm_export")

        self.export_button = QtWidgets.QPushButton("Export")

        self.statusBar().showMessage("Ready")

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("API key:", self.api_key_edit)
        form_layout.addRow("Username:", self.username_edit)

        dir_layout = QtWidgets.QHBoxLayout()
        dir_layout.addWidget(self.output_dir_edit)
        dir_layout.addWidget(self.browse_button)
        form_layout.addRow("Output directory:", dir_layout)

        form_layout.addRow("Base file name:", self.base_name_edit)
        form_layout.addRow("Output format:", self.format_combo)
        form_layout.addRow("", self.export_button)

        central_widget.setLayout(form_layout)

        self.browse_button.clicked.connect(self.on_browse_clicked)
        self.export_button.clicked.connect(self.on_export_clicked)

    def on_browse_clicked(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select output directory",
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def on_export_clicked(self) -> None:
        api_key = self.api_key_edit.text().strip()
        username = self.username_edit.text().strip()
        output_dir_str = self.output_dir_edit.text().strip()
        base_name = self.base_name_edit.text().strip() or "lastfm_export"

        if not api_key:
            QtWidgets.QMessageBox.warning(self, "Missing API key", "Please enter your Last.fm API key.")
            return

        if not username:
            QtWidgets.QMessageBox.warning(self, "Missing username", "Please enter the Last.fm username.")
            return

        if not output_dir_str:
            QtWidgets.QMessageBox.warning(self, "Missing output directory", "Please choose an output directory.")
            return

        output_dir = Path(output_dir_str)

        idx = self.format_combo.currentIndex()
        write_json = (idx == 0) or (idx == 2)
        write_csv = (idx == 1) or (idx == 2)

        self.export_button.setEnabled(False)
        self.statusBar().showMessage("Exporting...")

        try:
            client = LastFMClient(api_key=api_key)
            exporter = LastFMLibraryExporter(client, username=username)

            result: ExportResult = exporter.export_library(
                output_dir=output_dir,
                base_name=base_name,
                write_json=write_json,
                write_csv=write_csv,
            )

        except LastFMError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Last.fm error",
                f"An error occurred while talking to Last.fm:\n\n{exc}",
            )
            self.statusBar().showMessage("Error")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "File error",
                f"An error occurred while writing files:\n\n{exc}",
            )
            self.statusBar().showMessage("Error")
        else:
            msg_lines = [
                f"Exported library for user: {username}",
                f"Artists: {result.artists_count}",
                f"Albums:  {result.albums_count}",
            ]

            if result.json_path is not None:
                msg_lines.append(f"JSON file: {result.json_path}")

            if result.artists_csv_path is not None:
                msg_lines.append(f"Artists CSV: {result.artists_csv_path}")

            if result.albums_csv_path is not None:
                msg_lines.append(f"Albums CSV:  {result.albums_csv_path}")

            QtWidgets.QMessageBox.information(
                self,
                "Export complete",
                "\n".join(msg_lines),
            )
            self.statusBar().showMessage("Export complete")
        finally:
            self.export_button.setEnabled(True)


def run_app() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(600, 200)
    window.show()
    sys.exit(app.exec())
