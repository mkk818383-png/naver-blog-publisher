import re
import os
import sys
from html import escape

def convert_md_to_html(md_content):
    # Clean CRLF to LF
    md_content = md_content.replace('\r\n', '\n')

    # Parse custom media markdown: ![[사진/동영상 N: 캡션]]
    def replace_media(match):
        media_num = match.group(1).strip()
        caption = match.group(2).strip()
        emoji = "🎥" if "동영상" in media_num else "📷"
        media_type = "동영상" if "동영상" in media_num else "사진"
        return f'''<figure>
  <div class="photo-placeholder">{emoji} [{media_num}] {caption} (블로그 업로드 시 {media_type}으로 대체)</div>
  <figcaption>{caption}</figcaption>
</figure>'''

    md_content = re.sub(
        r'!\[\[((?:사진|동영상)\s*\d+)\s*:\s*([^\]]+)\]\]',
        replace_media,
        md_content
    )

    def replace_markdown_image(match):
        alt_text = escape(match.group(1).strip(), quote=True)
        image_url = escape(match.group(2).strip(), quote=True)
        return f'<figure><img src="{image_url}" alt="{alt_text}"></figure>'

    md_content = re.sub(
        r'!\[([^\]]+)\]\((https?://[^\s)]+)\)',
        replace_markdown_image,
        md_content
    )

    # Parse headers: ## heading -> <h2>heading</h2>
    md_content = re.sub(
        r'^###\s+(.+)$', r'<h3>\1</h3>', md_content, flags=re.MULTILINE
    )
    md_content = re.sub(
        r'^##\s+(.+)$', r'<h2>\1</h2>', md_content, flags=re.MULTILINE
    )
    md_content = re.sub(
        r'^#\s+(.+)$', r'<h1>\1</h1>', md_content, flags=re.MULTILINE
    )

    # Parse list items: - item -> <li>item</li>
    # Wrap consecutive <li> items in <ul>
    def replace_list(match):
        items = match.group(0).strip().split('\n')
        list_html = "<ul>\n"
        for item in items:
            item_content = re.sub(r'^-\s+', '', item)
            list_html += f"    <li>{item_content}</li>\n"
        list_html += "</ul>"
        return list_html

    md_content = re.sub(
        r'(?:^-\s+.+\n?)+', replace_list, md_content, flags=re.MULTILINE
    )

    # Parse paragraphs: wrap non-empty blocks that don't start with tags in <p>...</p>
    blocks = md_content.split('\n\n')
    html_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # If it's already an HTML block element (e.g. h2, figure, ul),
        # don't wrap it in <p>
        block_tags = ('<figure>', '<h2>', '<h3>', '<h1>', '<ul>', '<ol>')
        rendered_blocks = []
        if block.startswith(block_tags):
            rendered_blocks.append(block)
        else:
            rendered_blocks.extend(f"<div>{line}</div>" for line in block.split('\n') if line.strip())
        if rendered_blocks:
            if html_blocks:
                html_blocks.extend(('<div>&nbsp;</div>', '<div>&nbsp;</div>'))
            html_blocks.extend(rendered_blocks)

    return '\n\n'.join(html_blocks)


def compile_file(md_path, template_path, output_path):
    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found", file=sys.stderr)
        return False
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found", file=sys.stderr)
        return False

    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        html_body = convert_md_to_html(md_content)

        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        title_match = re.search(r'^#\s+(.+?)\s*$', md_content, flags=re.MULTILINE)
        page_title = escape(title_match.group(1).strip()) if title_match else '블로그 발행글'
        titled_template = re.sub(r'<title>.*?</title>', f'<title>{page_title}</title>', template_content, count=1, flags=re.DOTALL)
        final_html = titled_template.replace('<!-- CONTENT_PLACEHOLDER -->', html_body)

        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

        print(f"Success: Compiled {output_path}")
        return True
    except Exception as e:
        print(f"Error writing/reading files: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(
            "Usage: python3 compile.py <md_path> <template_path> <output_path>",
            file=sys.stderr
        )
        sys.exit(1)
    success = compile_file(sys.argv[1], sys.argv[2], sys.argv[3])
    if not success:
        sys.exit(1)
