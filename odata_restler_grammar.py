import argparse
import copy
import json
import os
import re
import subprocess

# Command line arguments
parser = argparse.ArgumentParser(description="This script generates RESTler working grammar from an ODATA service's OpenAPI specification.")

parser.add_argument("--output_dir", help="Output directory to generate the grammar in. If it is not specified, the directory will be created next to the provided OpenAPI spec file.", required=False)
parser.add_argument("--restler_bin_dir", help="Path to the compiled RESTler binary directory.", required=True)
parser.add_argument("--openapi_spec_file", help="Path to the OpenAPI spec file to generate grammar from.", required=True)

args = parser.parse_args()

if args.output_dir is None:
    output_dir = os.path.dirname(args.openapi_spec_file)
else:
    output_dir = os.path.realpath(args.output_dir)

# Functions
def process_openapi_spec(openapi_spec_file: str, output_dir: str) -> str:
    print(f"Processing {os.path.basename(openapi_spec_file)}...")

    with open(openapi_spec_file, "r") as f:
        # Deserialize JSON spec from file
        openapi_spec = json.load(f)
        new_spec = copy.deepcopy(openapi_spec)

        # Update spec
        for path in openapi_spec["paths"].keys():
            # Add '/' (slashes) around path parameters
            processed_path = re.sub(r"([^\/\\])(\{\w+\})([^\/\\])", r"\1__ADDED_SLASH__/\2/\3", path)

            # Update the path
            new_spec["paths"][processed_path] = new_spec["paths"].pop(path)

    output_spec_file = os.path.join(output_dir, "processed_openapi.json")
    with open(output_spec_file, "w") as f:
        # Serialize the new spec, replacing file content
        json.dump(new_spec, f, indent=2)

    return output_spec_file

def generate_restler_grammar(output_dir:str, restler_bin_dir: str, openapi_spec_file: str) -> None:
    # Create output directory if not already existing
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate config.json for RESTler compile
    config_file = os.path.join(output_dir, "compile_config.json")

    with open(config_file, "w") as f:
        config = {
            "TrackFuzzedParameterNames": True,
            "SwaggerSpecFilePath": [openapi_spec_file]
        }

        json.dump(config, f, indent=2)

    # Command to run RESTler compile
    restler_exe = f"{restler_bin_dir}/restler/Restler.exe"
    args = [restler_exe, "compile", config_file]
    
    # Run the command
    subprocess.call(args, cwd=output_dir)

def process_restler_grammar_py(output_dir: str) -> None:
    print("Processing grammar.py...")
    grammar_py_file = f"{output_dir}/Compile/grammar.py"

    with open(grammar_py_file, "r") as f:
        # Read grammar.py lines
        lines = f.readlines()

        # Process (remove slashes)
        for i, line in enumerate(lines):
            # Remove slashes in fuzzing grammar
            if re.match(r"\s*primitives\.restler_static_string\(\".*__ADDED_SLASH__\"\),", line) is not None:
                lines[i] = lines[i].replace("__ADDED_SLASH__", "")

                lines[i+1] = ""
                lines[i+3] = ""


    with open(grammar_py_file, "w") as f:
        # Update file content
        f.writelines(lines)

# Run
processed_openapi_spec = process_openapi_spec(args.openapi_spec_file, output_dir)

generate_restler_grammar(
    output_dir,
    os.path.realpath(args.restler_bin_dir),
    processed_openapi_spec
)
process_restler_grammar_py(output_dir)

print(f"Grammar generated and processed successfully in {os.path.join(output_dir, 'Compile')}")
