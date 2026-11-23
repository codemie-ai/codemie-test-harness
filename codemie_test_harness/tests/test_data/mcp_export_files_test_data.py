# Copyright 2026 EPAM Systems, Inc. (“EPAM”)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test data for files an MCP server exports as downloadable chat artifacts.

A stdio MCP server opted in with CODEMIE_EXPORT_FILES=true in its own env lets the
model export files it wrote with `codemie_export_files`; the back end stores them
in the conversation and links them as `sandbox:/v1/files/<token>`.

The filesystem MCP server writes text only, so the data covers the text types
(csv, json). Binary types (xlsx, zip, pdf) need a server that can write them.
"""

from dataclasses import dataclass

from codemie_sdk.models.assistant import MCPServerConfig, MCPServerDetails

from codemie_test_harness.tests.utils.base_utils import get_random_name

EXPORT_FILES_ENV_KEY = "CODEMIE_EXPORT_FILES"
SANDBOX_FILE_LINK_PREFIX = "sandbox:/v1/files/"
MCP_FILES_FOLDER = "/home/codemie"
# The folder a model writes to. MCP-Connect swaps it for the caller's own per-chat folder
# in the arguments of an opted-in call, so nothing a test writes lands at MCP_FILES_FOLDER
# itself, where it would pile up in the listing other tests compare (the filesystem server
# has no delete tool).
EXPORT_FOLDER = f"{MCP_FILES_FOLDER}/codemie_export"

# The answer must carry the link, so the API tests can read the token from it.
EXPORT_WITH_LINKS_SYSTEM_PROMPT = (
    "You write files with the filesystem tools and deliver them with the "
    "codemie_export_files argument of a tool call. After exporting, list the download "
    "link of every exported file in your answer exactly as the tool returned it."
)

# A link in the answer renders as an inline chip. The generated-files block lists only
# the files that are not linked inline, so the UI tests ask the model not to repeat them.
EXPORT_WITHOUT_LINKS_SYSTEM_PROMPT = (
    "You write files with the filesystem tools and deliver them with the "
    "codemie_export_files argument of a tool call. Do not put download links or file "
    "paths in your answer; only say whether the export worked."
)


@dataclass(frozen=True)
class ExportFile:
    """A text file the model writes on the MCP server and exports."""

    name: str
    content: str
    mime_type: str

    @property
    def path(self) -> str:
        return f"{EXPORT_FOLDER}/{self.name}"


def build_csv_file() -> ExportFile:
    return ExportFile(
        name=f"{get_random_name()}.csv",
        content="id,name\n1,alpha\n2,beta",
        mime_type="text/csv",
    )


def build_json_file() -> ExportFile:
    return ExportFile(
        name=f"{get_random_name()}.json",
        content='{"id": 1, "name": "alpha"}',
        mime_type="application/json",
    )


def export_prompt(file: ExportFile) -> str:
    """Ask the model to write `file` and export it."""
    return (
        f"Write a file {file.path} with exactly this content:\n{file.content}\n"
        "Then export that file with the codemie_export_files tool and tell me the result."
    )


def export_missing_file_prompt() -> str:
    """Ask the model to export a file that was never written."""
    return (
        f"Export the file {EXPORT_FOLDER}/{get_random_name()}-missing.csv with the "
        "codemie_export_files tool and tell me the result."
    )


def export_empty_file_prompt() -> str:
    """Ask the model to write an empty file and export it."""
    return (
        f"Create an empty file {EXPORT_FOLDER}/{get_random_name()}-empty.csv with no "
        "content, then export that file with the codemie_export_files tool and tell me "
        "the result."
    )


# ---------------------------------------------------------------------------------------
# Binary files written by a shell MCP server (python3 -c)
#
# MCP-Connect replaces EXPORT_FOLDER in every string argument of an opted-in call with the
# caller's own export folder, so a script that writes under EXPORT_FOLDER lands where the
# export accepts it (mcp_connect/client/export.py `_fill` and `prepare`). cli-mcp-server refuses the shell operators ; | < > && and any flag not
# in ALLOWED_FLAGS, so each script is one statement-free list expression, and markup
# characters are written as placeholders that the script translates itself:
#   {  ->  <     }  ->  >     #  ->  "
# ---------------------------------------------------------------------------------------

SHELL_MCP_SERVER = MCPServerDetails(
    name="Shell MCP server for file export",
    description="CLI MCP server that runs python3 and exports the files it writes",
    enabled=True,
    config=MCPServerConfig(
        command="uvx",
        # Pin `mcp` below 2.0.0: cli-mcp-server declares an unpinned `mcp>=1.10.1`
        # dependency, and mcp==2.0.0 renamed `Server.list_tools`, breaking it.
        args=["--with", "mcp<2.0.0", "cli-mcp-server"],
        env={
            "ALLOWED_DIR": MCP_FILES_FOLDER,
            "ALLOWED_COMMANDS": "python3",
            "ALLOWED_FLAGS": "-c",
            "MAX_COMMAND_LENGTH": "2500",
            EXPORT_FILES_ENV_KEY: "true",
        },
    ),
)

_MARKUP = '(lambda s:s.replace("{",chr(60)).replace("}",chr(62)).replace("#",chr(34)))'
_OPC = "http://schemas.openxmlformats.org/"

XLSX_MEMBERS = (
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/worksheets/sheet1.xml",
)
ZIP_MEMBERS = {"first.txt": "alpha", "second.txt": "beta"}
PDF_TEXT = (
    "%PDF-1.4\\n1 0 obj\\n{{/Type /Catalog /Pages 2 0 R}}\\nendobj\\n"
    "2 0 obj\\n{{/Type /Pages /Kids [3 0 R] /Count 1}}\\nendobj\\n"
    "3 0 obj\\n{{/Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]}}\\nendobj\\n"
    "trailer\\n{{/Root 1 0 R}}\\n%%EOF\\n"
)
PDF_BYTES = (
    "%PDF-1.4\n1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
    "2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
    "3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]>>\nendobj\n"
    "trailer\n<</Root 1 0 R>>\n%%EOF\n"
).encode()


def _zip_script(path: str, members: list) -> str:
    """List expression that writes a zip at `path`; members are (name, markup text) pairs."""
    writes = ",".join(f'z.writestr("{name}",t("{text}"))' for name, text in members)
    return f'[t:={_MARKUP},z:=__import__("zipfile").ZipFile("{path}","w"),{writes},z.close()]'


def _xlsx_script(path: str) -> str:
    rel_ns = f"{_OPC}package/2006/relationships"
    main_ns = f"{_OPC}spreadsheetml/2006/main"
    doc_rel = f"{_OPC}officeDocument/2006/relationships"
    content_types = (
        f"{{?xml version=#1.0#?}}{{Types xmlns=#{_OPC}package/2006/content-types#}}"
        "{Default Extension=#rels# ContentType=#application/vnd.openxmlformats-package.relationships+xml#/}"
        "{Default Extension=#xml# ContentType=#application/xml#/}"
        "{Override PartName=#/xl/workbook.xml# ContentType=#application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml#/}"
        "{Override PartName=#/xl/worksheets/sheet1.xml# ContentType=#application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml#/}"
        "{/Types}"
    )
    root_rels = (
        f"{{Relationships xmlns=#{rel_ns}#}}"
        f"{{Relationship Id=#rId1# Type=#{doc_rel}/officeDocument# Target=#xl/workbook.xml#/}}"
        "{/Relationships}"
    )
    workbook = (
        f"{{workbook xmlns=#{main_ns}# xmlns:r=#{doc_rel}#}}"
        "{sheets}{sheet name=#Sheet1# sheetId=#1# r:id=#rId1#/}{/sheets}{/workbook}"
    )
    workbook_rels = (
        f"{{Relationships xmlns=#{rel_ns}#}}"
        f"{{Relationship Id=#rId1# Type=#{doc_rel}/worksheet# Target=#worksheets/sheet1.xml#/}}"
        "{/Relationships}"
    )
    sheet = f"{{worksheet xmlns=#{main_ns}#}}{{sheetData/}}{{/worksheet}}"
    return _zip_script(
        path,
        [
            (XLSX_MEMBERS[0], content_types),
            (XLSX_MEMBERS[1], root_rels),
            (XLSX_MEMBERS[2], workbook),
            (XLSX_MEMBERS[3], workbook_rels),
            (XLSX_MEMBERS[4], sheet),
        ],
    )


def _plain_zip_script(path: str) -> str:
    return _zip_script(path, list(ZIP_MEMBERS.items()))


def _pdf_script(path: str) -> str:
    return f'[t:={_MARKUP},f:=open("{path}","wb"),f.write(t("{PDF_TEXT}").encode()),f.close()]'


@dataclass(frozen=True)
class ShellExportFile:
    """A binary file the model writes by running `command` on the shell MCP server."""

    name: str
    mime_type: str
    command: str
    signature: bytes
    zip_members: tuple
    contains: bytes  # bytes the script wrote that the download must hold

    @property
    def path(self) -> str:
        return f"{EXPORT_FOLDER}/{self.name}"


def _shell_file(extension, mime_type, script_for, signature, zip_members, contains):
    name = f"{get_random_name()}.{extension}"
    script = script_for(f"{EXPORT_FOLDER}/{name}")
    return ShellExportFile(
        name=name,
        mime_type=mime_type,
        command=f"python3 -c '{script}'",
        signature=signature,
        zip_members=tuple(zip_members),
        contains=contains,
    )


def build_xlsx_file() -> ShellExportFile:
    return _shell_file(
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _xlsx_script,
        b"PK",
        XLSX_MEMBERS,
        b"xl/workbook.xml",
    )


def build_zip_file() -> ShellExportFile:
    return _shell_file(
        "zip",
        "application/zip",
        _plain_zip_script,
        b"PK",
        tuple(ZIP_MEMBERS),
        b"first.txt",
    )


def build_pdf_file() -> ShellExportFile:
    return _shell_file("pdf", "application/pdf", _pdf_script, b"%PDF-", (), PDF_BYTES)


def shell_export_prompt(file: ShellExportFile) -> str:
    """Ask the model to run the script that writes `file`, then export it."""
    return (
        "Call the run_command tool with exactly this command, unchanged:\n"
        f"{file.command}\n"
        f"Then export the file {file.path} with the codemie_export_files tool and tell "
        "me the result."
    )


# ---------------------------------------------------------------------------------------
# More files than one result may deliver
# ---------------------------------------------------------------------------------------

# One export call delivers at most this many files; the rest become a refusal note.
MAX_DELIVERED_FILES = 20
FILES_WRITTEN = MAX_DELIVERED_FILES + 1


@dataclass(frozen=True)
class ManyFilesExport:
    """One shell command that writes FILES_WRITTEN small files, and their paths."""

    command: str
    paths: tuple


def build_many_files_export() -> ManyFilesExport:
    prefix = get_random_name()
    script = (
        f'[__import__("pathlib").Path(f"{EXPORT_FOLDER}/{prefix}-{{i}}.txt")'
        f'.write_text(f"file {{i}}") for i in range({FILES_WRITTEN})]'
    )
    return ManyFilesExport(
        command=f"python3 -c '{script}'",
        paths=tuple(f"{EXPORT_FOLDER}/{prefix}-{i}.txt" for i in range(FILES_WRITTEN)),
    )


def many_files_export_prompt(batch: ManyFilesExport) -> str:
    """Ask for one run_command call that writes the files and exports every path."""
    return (
        "Make exactly one call of the run_command tool, with this command unchanged:\n"
        f"{batch.command}\n"
        "and with the codemie_export_files argument of that same call set to all "
        f"{len(batch.paths)} of these paths, in one list:\n"
        + "\n".join(batch.paths)
        + "\nDo not call any other tool. Then tell me the result."
    )
