import xmltodict
import re
import click
from utils import *

load_dotenv()

# tei_path = os.path.join("..", "data", "TEI_XML")  # Path to the directory containing the TEI XML files
# json_path = os.path.join("..", "data", "JSON_References")  # Path to the directory where the JSON files will be saved
# logs_path = os.path.join("..", "logs")  # Path to the directory where logs will be saved
logs_path = get_keys()['logs_path']
json_path = get_keys()['json_path']
tei_path = get_keys()['tei_path']


logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(logs_path, f"{os.path.basename(__file__).replace('.py', '.log')}"))
    ]
)


def get_jsonfilename(fl, json_path, complete_path):
    """
    Returns the name of the output JSON file based on the name of the input TEI XML file. If `complete_path` is True, returns the full path to the output JSON file.

    :param fl: A file object representing the input TEI XML file.
    :param json_path: The path to the directory where the JSON files will be saved.
    :param complete_path: A boolean value indicating whether to return the complete path to the output file.
    "return: The name of the output JSON file (either with or without the full path).
    """
    if complete_path is True:
        return os.path.join(json_path, fl.name.replace('.tei.xml', '.json'))
    else:
        return fl.name.replace('.tei.xml', '.json')


def fix_formatting(json_data):
    """
    Fixes formatting errors such as multiple whitespaces, newline characters and hyphenation errors.

    :param json_data: The JSON string to be formatted.
    :return: The formatted JSON string.
    """
    json_data = re.sub(r'\s{2,}', ' ', json_data)
    json_data = re.sub(r'\\n', '', json_data)
    json_data = re.sub(r'- ', '', json_data)

    return json_data


def convert_xml2json(xml_file, fl, json_path):
    """
    Converts the contents of `xml_file` from TEI XML format to JSON and writes the output to a file with the same name as `fl`, but with the '.json' extension. The output file is saved in the directory specified by `json_path`.

    :param xml_file: A file object representing the input TEI XML file.
    :param fl: A file object representing the output JSON file.
    :param json_path: The path to the directory where the JSON files will be saved.
    :return: None
    """
    data_dict = xmltodict.parse(xml_file.read())
    data_dict = data_dict["TEI"]["text"]["back"]["div"]["listBibl"]

    json_data = fix_formatting(json.dumps(data_dict))

    with open(get_jsonfilename(fl, json_path, True), "w", encoding="utf8") as json_file:
        json_file.write(json_data)


def batch_convert_files(in_path, out_path):
    """
    Converts all TEI XML files in `in_path` to JSON and saves them in the directory specified by `out_path`.

    :param in_path: The path to the directory containing the input TEI XML files.
    :param out_path: The path to the directory where the JSON files will be saved.
    :return: None
    """
    for fl in os.scandir(in_path):
        if fl.is_file() and fl.name.endswith(".xml") and not os.path.exists(get_jsonfilename(fl, out_path, True)):
            logging.info(f"Successfully created {get_jsonfilename(fl, out_path, False)}.")
            click.echo(f"Successfully created {get_jsonfilename(fl, out_path, False)}.")

            with open(fl, encoding="utf8") as xml_file:
                convert_xml2json(xml_file, fl, out_path)
        elif (os.path.exists(get_jsonfilename(fl, out_path, True))):
            logging.info(f"{get_jsonfilename(fl, out_path, False)} already exists.")
            click.echo(f"{get_jsonfilename(fl, out_path, False)} already exists.")
        else:
            logging.info(f"{fl.name} is not a valid TEI XML file.")
            click.echo(f"{fl.name} is not a valid TEI XML file.")


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    '--in_path',
    type=click.STRING,
    default=tei_path,
    help="The path to the directory containing the TEI files."
)
@click.option(
    '--out_path',
    type=click.STRING,
    default=json_path,
    help="The path to the directory where the JSON files will be saved."
)
@click.option(
    '--yes',
    is_flag=True
)
def main(ctx, in_path, out_path, yes):
    """
    Converts TEI XML files containing bibliographic references to JSON files.

    :param ctx: The Click context.
    :param in_path: The path to the directory containing the TEI XML files.
    :param out_path: The path to the directory where the output JSON files will be saved.
    :param yes: Flag to auro create output directory if it does not exist.
    :return: None
    """

    if ctx.invoked_subcommand is None:
        # Check if the logs folder exists, create it if it does not exist
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)

        # Check if the default input folder exists, create it if it does not exist
        if in_path == tei_path:
            if not os.path.exists(in_path):
                os.makedirs(in_path)

        # Check if the default output folder exists, create it if it does not exist
        if out_path == json_path:
            if not os.path.exists(out_path):
                os.makedirs(out_path)

        # Check if the input folder exists
        if not os.path.exists(in_path):
            click.echo(f"The folder \"{in_path}\" does not exist. Please create it and add the TEI files to it.")
            exit(1)
        else:
            # Check if the input folder is empty
            if len(os.listdir(in_path)) == 0:
                click.echo(f"\"{in_path}\" folder is empty. Please add some TEI XML files.")
                exit(1)
            else:
                # Check if the output folder exists, and create it if not
                if not os.path.exists(out_path):
                    if not yes:
                        if click.confirm(f"The folder \"{out_path}\" does not exist. Do you want to create it?"):
                            os.makedirs(out_path)
                            click.echo(f"Successfully created \"{out_path}\" folder.")
                        else:
                            exit(1)
                    else:
                        os.makedirs(out_path)
                        click.echo(f"Successfully created \"{out_path}\" folder.")

                # Process the files in the input folder
                batch_convert_files(in_path, out_path)


if __name__ == "__main__":
    main()
