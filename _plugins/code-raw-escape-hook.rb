# frozen_string_literal: true

# _plugins/code-raw-escape-hook.rb
#
# Automatically escapes Liquid delimiters (`{{`, `{%`) inside Markdown fenced code blocks
# (``` / ~~~) and inline code spans (`...`) during `:site, :post_read`, so authors never
# need to wrap code snippets with manual `{% raw %}...{% endraw %}` tags.
#
# Design notes:
# - Uses token-level escaping (`{{` -> `{% raw %}{{{% endraw %}`, `{%` -> `{% raw %}{%{% endraw %}`),
#   avoiding nested-raw syntax errors.
# - Leaves Liquid tags outside code (e.g. `{% linkpreview "URL" %}`) untouched.
# - Preserves any existing manual `{% raw %}...{% endraw %}` directives (both outside and inside
#   code blocks/spans) for 100% backwards compatibility with existing posts.
# - Also escapes `post.data['excerpt']` so index/feed previews never break on code spans.
# - Opt out per post by setting `auto_raw_code: false` in Front Matter.

module CodeRawEscapeHook
  RAW_OPEN_RE = /\{%-?\s*raw\s*-?%\}/
  RAW_CLOSE_RE = /\{%-?\s*endraw\s*-?%\}/
  RAW_BLOCK_RE = /\{%-?\s*raw\s*-?%\}.*?\{%-?\s*endraw\s*-?%\}/m
  LIQUID_OPEN_RE = /\{\{|\{%/
  FENCE_OPEN_RE = /\A((?:[ \t]*>[ \t]?)*[ \t]{0,3})(`{3,}|~{3,})([^\r\n]*)\r?\n?\z/

  def self.escape_liquid_delimiters(text)
    return text unless text.match?(LIQUID_OPEN_RE)

    text.gsub(LIQUID_OPEN_RE) { |m| "{% raw %}#{m}{% endraw %}" }
  end

  def self.escape_preserving_raw_blocks(text)
    return text unless text.match?(LIQUID_OPEN_RE)
    return escape_liquid_delimiters(text) unless text.match?(RAW_BLOCK_RE)

    out = +''
    pos = 0
    text.scan(RAW_BLOCK_RE) do
      m = Regexp.last_match
      out << escape_liquid_delimiters(text[pos...m.begin(0)]) if m.begin(0) > pos
      out << m[0]
      pos = m.end(0)
    end
    out << escape_liquid_delimiters(text[pos..]) if pos < text.length
    out
  end

  def self.escape_inline_code_in_prose(text)
    return text unless text.include?('`') && text.match?(LIQUID_OPEN_RE)

    out = +''
    i = 0
    len = text.length

    while i < len
      if text[i] == '`'
        tick_start = i
        i += 1 while i < len && text[i] == '`'
        tick_len = i - tick_start
        ticks = text[tick_start, tick_len]

        search_pos = i
        close_start = nil
        while search_pos < len
          idx = text.index('`', search_pos)
          break unless idx

          run_end = idx
          run_end += 1 while run_end < len && text[run_end] == '`'
          if (run_end - idx) == tick_len
            close_start = idx
            break
          end
          search_pos = run_end
        end

        if close_start
          inner = text[i...close_start]
          out << ticks << escape_preserving_raw_blocks(inner) << ticks
          i = close_start + tick_len
        else
          out << ticks
        end
      else
        next_tick = text.index('`', i)
        if next_tick
          out << text[i...next_tick]
          i = next_tick
        else
          out << text[i..]
          break
        end
      end
    end

    out
  end

  def self.escape_prose(prose)
    return prose unless prose.include?('`') && prose.match?(LIQUID_OPEN_RE)

    out = +''
    pos = 0
    prose.scan(RAW_BLOCK_RE) do
      m = Regexp.last_match
      prefix = prose[pos...m.begin(0)]
      next if prefix.count('`').odd?

      out << escape_inline_code_in_prose(prefix) unless prefix.empty?
      out << m[0]
      pos = m.end(0)
    end
    out << escape_inline_code_in_prose(prose[pos..]) if pos < prose.length
    out
  end

  def self.opens_multiline_raw?(line, in_fence:)
    return false unless line.match?(RAW_OPEN_RE)

    stripped = in_fence ? line : line.gsub(/(`+)(?!`).+?(?<!`)\1(?!`)/, '')
    stripped = stripped.gsub(RAW_BLOCK_RE, '')
    stripped.match?(RAW_OPEN_RE)
  end

  def self.escape_markdown(content)
    return content if content.nil? || content.empty?
    return content unless content.match?(LIQUID_OPEN_RE)

    out = +''
    prose_buf = +''
    in_fence = false
    in_manual_raw = false
    fence_char = nil
    fence_len = 0
    bq_depth = 0

    content.each_line do |line|
      if in_manual_raw
        out << line
        in_manual_raw = false if line.match?(RAW_CLOSE_RE)
        next
      end

      if !in_fence
        if opens_multiline_raw?(line, in_fence: false)
          unless prose_buf.empty?
            out << escape_prose(prose_buf)
            prose_buf = +''
          end
          in_manual_raw = true
          out << line
          next
        end

        if (m = FENCE_OPEN_RE.match(line))
          prefix = m[1]
          ticks = m[2]
          info = m[3]
          if ticks[0] == '~' || !info.include?('`')
            unless prose_buf.empty?
              out << escape_prose(prose_buf)
              prose_buf = +''
            end
            in_fence = true
            fence_char = ticks[0]
            fence_len = ticks.length
            bq_depth = prefix.count('>')
            out << line
            next
          end
        end

        prose_buf << line
      else
        stripped = bq_depth.positive? ? line.sub(/\A(?:[ \t]*>[ \t]?){0,#{bq_depth}}/, '') : line
        if stripped.match?(/\A[ \t]{0,3}#{Regexp.escape(fence_char)}{#{fence_len},}[ \t]*\r?\n?\z/)
          in_fence = false
          fence_char = nil
          fence_len = 0
          bq_depth = 0
          out << line
        elsif opens_multiline_raw?(line, in_fence: true)
          in_manual_raw = true
          out << line
        else
          out << escape_preserving_raw_blocks(line)
        end
      end
    end

    out << escape_prose(prose_buf) unless prose_buf.empty?
    out
  end
end

Jekyll::Hooks.register :site, :post_read do |site|
  site.posts.docs.each do |doc|
    next if doc.data['render_with_liquid'] == false
    next if doc.data['auto_raw_code'] == false

    original = doc.content
    escaped = CodeRawEscapeHook.escape_markdown(original)
    next if escaped == original

    doc.content = escaped
    if doc.data['excerpt'].respond_to?(:content) && doc.data['excerpt'].respond_to?(:content=)
      doc.data['excerpt'].content = CodeRawEscapeHook.escape_markdown(doc.data['excerpt'].content)
    end
  end
end
