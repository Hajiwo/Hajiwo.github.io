(() => {
  'use strict';

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
    })[character]);
  }

  function inlineMarkdown(value) {
    return value
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>');
  }

  function renderMarkdown(source) {
    const lines = escapeHtml(source).split('\n');
    const output = [];
    let inCode = false;
    let listOpen = false;

    for (const line of lines) {
      if (line.startsWith('```')) {
        if (listOpen) { output.push('</ul>'); listOpen = false; }
        output.push(inCode ? '</code></pre>' : '<pre><code>');
        inCode = !inCode;
        continue;
      }
      if (inCode) { output.push(`${line}\n`); continue; }

      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      const listItem = line.match(/^[-*]\s+(.+)$/);
      if (listItem) {
        if (!listOpen) { output.push('<ul>'); listOpen = true; }
        output.push(`<li>${inlineMarkdown(listItem[1])}</li>`);
        continue;
      }
      if (listOpen) { output.push('</ul>'); listOpen = false; }
      if (heading) {
        const level = heading[1].length;
        output.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      } else if (line.startsWith('&gt; ')) {
        output.push(`<blockquote>${inlineMarkdown(line.slice(5))}</blockquote>`);
      } else if (line.trim()) {
        output.push(`<p>${inlineMarkdown(line)}</p>`);
      }
    }
    if (listOpen) output.push('</ul>');
    if (inCode) output.push('</code></pre>');
    return output.join('');
  }

  function setupEditor({ bodyId, descriptionId, previewPanelId, previewId, countsId, emptyCopy, language }) {
    const body = document.querySelector(`#${bodyId}`);
    const description = document.querySelector(`#${descriptionId}`);
    const previewPanel = document.querySelector(`#${previewPanelId}`);
    const preview = document.querySelector(`#${previewId}`);
    const counts = document.querySelector(`#${countsId}`);
    const fieldName = bodyId.replace(/^id_/, '');
    const bodyRow = document.querySelector(`.form-row.field-${fieldName}`);
    if (!body || !previewPanel || !preview || !counts || !bodyRow) return;

    const grid = document.createElement('div');
    grid.className = 'markdown-editor-grid';
    bodyRow.parentNode.insertBefore(grid, bodyRow);
    grid.append(bodyRow, previewPanel);
    previewPanel.hidden = false;

    function update() {
      const source = body.value || '';
      preview.innerHTML = source.trim()
        ? renderMarkdown(source)
        : `<p class="preview-empty">${emptyCopy}</p>`;
      const words = source.trim() ? source.trim().split(/\s+/).length : 0;
      counts.textContent = language === 'zh'
        ? `${source.length} 字符 · ${words} 词`
        : `${source.length} characters · ${words} words`;
      if (description) {
        const counter = document.querySelector(`#${descriptionId}-count`);
        if (counter) counter.textContent = `${description.value.length}/500`;
      }
    }

    if (description) {
      const counter = document.createElement('span');
      counter.id = `${descriptionId}-count`;
      counter.className = 'field-counter';
      description.insertAdjacentElement('afterend', counter);
      description.addEventListener('input', update);
    }
    body.addEventListener('input', update);
    update();
  }

  function initEditor() {
    setupEditor({
      bodyId: 'id_body',
      descriptionId: 'id_description',
      previewPanelId: 'markdown-preview-panel-zh',
      previewId: 'markdown-preview-zh',
      countsId: 'article-counts-zh',
      emptyCopy: '中文正文预览会显示在这里。',
      language: 'zh',
    });
    setupEditor({
      bodyId: 'id_body_en',
      descriptionId: 'id_description_en',
      previewPanelId: 'markdown-preview-panel-en',
      previewId: 'markdown-preview-en',
      countsId: 'article-counts-en',
      emptyCopy: 'The English body preview appears here.',
      language: 'en',
    });
  }

  document.addEventListener('DOMContentLoaded', initEditor);
})();
