import re
import os
import sys

def convert_md_to_html(md_content):
    # Clean CRLF to LF
    md_content = md_content.replace('\r\n', '\n')

    # Parse custom image markdown: ![[사진 N: 캡션]]
    def replace_image(match):
        photo_num = match.group(1).strip()
        caption = match.group(2).strip()
        return f'''<figure>
  <div class="photo-placeholder">📷 [{photo_num}] {caption} (블로그 업로드 시 사진으로 대체)</div>
  <figcaption>{caption}</figcaption>
</figure>'''

    md_content = re.sub(
        r'!\[\[(사진\s*\d+)\s*:\s*([^\]]+)\]\]',
        replace_image,
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
        if block.startswith(block_tags):
            html_blocks.append(block)
        else:
            # Wrap newlines inside a paragraph with <br> to preserve line breaks
            paragraph_html = block.replace('\n', '<br>')
            html_blocks.append(f"<p>{paragraph_html}</p>")

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

        final_html = template_content.replace('<!-- CONTENT_PLACEHOLDER -->', html_body)

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

