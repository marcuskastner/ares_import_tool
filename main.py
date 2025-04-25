import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import requests
from urllib.parse import urlparse
import sys
from colorama import init, Fore

# Initialize colorama for Windows compatibility
init(autoreset=True)

# Load the environment variables from the .env file
load_dotenv()


class ImportTool:
    def __init__(self):
        self.file_path = None
        self.soup = None
        self.images = set()
        self.fonts = set()
        self.images_dir = None
        self.fonts_dir = None

    def run(self):
        """Starts the import process."""
        self.ask_file_path()
        if self.file_path:
            self.construct_directories()
            self.process_file()
            self.download_resources()
            self.print_results()
            print(Fore.GREEN + "✅ All done! Happy Hacking! 🎉")
            sys.exit()
        else:
            print(Fore.RED + "❌ No file selected.")
            sys.exit()

    def ask_file_path(self):
        """Asks the user for the theme directory and file to process."""
        base_dir = os.getenv('ARES_BE5_DIR')
        if not base_dir:
            print(Fore.RED + "❌ ARES_BE5_DIR is not set in your .env file.")
            sys.exit()

        themes_dir = os.path.join(base_dir, 'templates', 'themes')

        if not os.path.isdir(themes_dir):
            print(Fore.RED + f"❌ The directory {themes_dir} does not exist.")
            sys.exit()

        themes = [d for d in os.listdir(themes_dir) if os.path.isdir(os.path.join(themes_dir, d))]
        if not themes:
            print(Fore.YELLOW + f"⚠️ No themes found in {themes_dir}.")
            sys.exit()

        print(Fore.BLUE + "Available themes:")
        for i, theme in enumerate(themes, 1):
            print(Fore.CYAN + f"{i}. {theme}")

        try:
            theme_choice = int(input(Fore.YELLOW + "Select a theme (enter the number): "))
            if theme_choice < 1 or theme_choice > len(themes):
                print(Fore.RED + "❌ Invalid theme choice.")
                sys.exit()
        except ValueError:
            print(Fore.RED + "❌ Please enter a valid number.")
            sys.exit()

        selected_theme = themes[theme_choice - 1]
        theme_path = os.path.join(themes_dir, selected_theme)

        theme_files = [f for f in os.listdir(theme_path) if os.path.isfile(os.path.join(theme_path, f))]
        if not theme_files:
            print(Fore.YELLOW + f"⚠️ No files found in {theme_path}.")
            sys.exit()

        print(Fore.BLUE + "Available files:")
        for i, file in enumerate(theme_files, 1):
            print(Fore.CYAN + f"{i}. {file}")

        try:
            file_choice = int(input(Fore.YELLOW + "Select a file (enter the number): "))
            if file_choice < 1 or file_choice > len(theme_files):
                print(Fore.RED + "❌ Invalid file choice.")
                sys.exit()
        except ValueError:
            print(Fore.RED + "❌ Please enter a valid number.")
            sys.exit()

        selected_file = theme_files[file_choice - 1]
        self.file_path = os.path.join(theme_path, selected_file)

    def construct_directories(self):
        """Constructs the images and fonts directories based on the HTML file path."""
        base_dir = os.path.dirname(self.file_path)
        file_name = os.path.basename(self.file_path)
        dir_name = file_name.rsplit('-', 1)[-1].split('.')[0]  # Extract '2024Jul' from 'wrap-2024Jul.html.twig'

        self.images_dir = os.path.join(base_dir.replace('/templates', '/web'), 'images', dir_name)
        self.fonts_dir = os.path.join(base_dir.replace('/templates', '/web'), 'fonts', dir_name)

        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)
        print(Fore.GREEN + "📂 Directories created successfully.")

    def process_file(self):
        """Processes the selected file to extract images and fonts."""
        self.load_soup()
        self.extract_images_from_tags()
        self.extract_images_and_fonts_from_styles()

    def load_soup(self):
        """Loads the BeautifulSoup object with HTML content."""
        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        self.soup = BeautifulSoup(content, 'html.parser')

    def extract_images_from_tags(self):
        """Extracts image paths from <img> tags."""
        img_tags = self.soup.find_all('img')
        img_paths = [img['src'] for img in img_tags if 'src' in img.attrs]
        self.images.update(img_paths)

    def extract_images_and_fonts_from_styles(self):
        """Extracts image and font paths from <style> tags and inline styles."""
        image_regex = re.compile(r'url\s*\(\s*[\'"]?([^\'")]+\.(?:png|jpg|jpeg|gif|svg|webp))[\'"]?\s*\)',
                                 re.IGNORECASE)
        font_regex = re.compile(r'src\s*:\s*url\s*\(\s*[\'"]?([^\'")]+\.(?:woff|woff2|ttf|otf|eot))[\'"]?\s*\)',
                                re.IGNORECASE)

        style_tags = self.soup.find_all('style')
        inline_style_elements = self.soup.find_all(lambda tag: 'style' not in tag.name and tag.has_attr('style'))

        for style in style_tags:
            content = style.string or ''
            self.images.update(image_regex.findall(content))
            self.fonts.update(font_regex.findall(content))

        for element in inline_style_elements:
            inline_style = element['style']
            self.images.update(image_regex.findall(inline_style))
            self.fonts.update(font_regex.findall(inline_style))

    def download_resources(self):
        """Downloads images and fonts and updates references in the original file."""
        for image_url in self.images:
            self.download_and_replace(image_url, self.images_dir)

        for font_url in self.fonts:
            self.download_and_replace(font_url, self.fonts_dir)

        with open(self.file_path, 'w', encoding='utf-8') as file:
            file.write(str(self.soup))

    def download_and_replace(self, url, save_dir):
        """Downloads a resource and replaces its reference in the HTML."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            filename = os.path.basename(urlparse(url).path)
            file_path = os.path.join(save_dir, filename)
            with open(file_path, 'wb') as file:
                file.write(response.content)

            new_path = os.path.relpath(file_path, os.path.dirname(self.file_path)).split('/web', 1)[-1]

            for tag in self.soup.find_all(src=url):
                tag['src'] = "{{asset( '" + new_path + "' )}}"
            for tag in self.soup.find_all(style=True):
                tag['style'] = tag['style'].replace(url, new_path)
            for style in self.soup.find_all('style'):
                if style.string:
                    style.string = style.string.replace(url, new_path)

            print(Fore.GREEN + f"✅ Downloaded: {filename}")

        except requests.RequestException as e:
            print(Fore.RED + f"❌ Failed to download {url}: {e}")

    def print_results(self):
        """Prints the collected images and fonts."""
        print(Fore.BLUE + "📷 Images:", Fore.CYAN + str(self.images))
        print(Fore.BLUE + "🔤 Fonts:", Fore.CYAN + str(self.fonts))


if __name__ == "__main__":
    importTool = ImportTool()
    importTool.run()
