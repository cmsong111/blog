# frozen_string_literal: true

# _plugins/image-dimensions-hook.rb
#
# Automatically injects intrinsic `width` and `height` attributes onto local <img> tags
# during post-render using FastImage, preventing Cumulative Layout Shift (CLS) without
# requiring manual dimensions in every Markdown post.

require 'fastimage'
require 'uri'

module ImageDimensionsHook
  @size_cache = {}

  def self.dimensions_for(file_path)
    return @size_cache[file_path] if @size_cache.key?(file_path)

    @size_cache[file_path] =
      if File.file?(file_path)
        FastImage.size(file_path)
      end
  rescue StandardError
    @size_cache[file_path] = nil
  end

  def self.extract_local_asset_path(src, cdn_prefix, baseurl)
    return nil if src.nil? || src.empty? || src.start_with?('data:')

    path = src.dup
    if cdn_prefix && !cdn_prefix.empty? && path.start_with?(cdn_prefix)
      path = path.delete_prefix(cdn_prefix)
    elsif path.start_with?('http://', 'https://', '//')
      return nil
    end

    if baseurl && !baseurl.empty? && path.start_with?(baseurl)
      path = path.delete_prefix(baseurl)
    end

    path = path.split(/[?#]/, 2).first
    path = URI.decode_www_form_component(path)
    return nil unless path.start_with?('/assets/')

    path.delete_prefix('/')
  rescue ArgumentError
    nil
  end

  def self.inject_dimensions(doc)
    return unless doc.output && doc.output.include?('<img ')

    cdn_prefix = doc.site.config['cdn'].to_s.chomp('/')
    baseurl = doc.site.config['baseurl'].to_s.chomp('/')
    source_dir = doc.site.source

    doc.output = doc.output.gsub(/<img\b[^>]*>/i) do |tag|
      if tag.match?(/\bwidth\s*=/i) && tag.match?(/\bheight\s*=/i)
        next tag
      end

      src_match = tag.match(/\b(?:data-src|src)\s*=\s*"([^"]+)"/i)
      next tag unless src_match

      rel_path = extract_local_asset_path(src_match[1], cdn_prefix, baseurl)
      next tag unless rel_path

      dims = dimensions_for(File.join(source_dir, rel_path))
      next tag unless dims && dims[0].to_i.positive? && dims[1].to_i.positive?

      attrs = +''
      attrs << " width=\"#{dims[0]}\"" unless tag.match?(/\bwidth\s*=/i)
      attrs << " height=\"#{dims[1]}\"" unless tag.match?(/\bheight\s*=/i)

      tag.sub(%r{\s*/?>\z}, "#{attrs}\\0")
    end
  end
end

Jekyll::Hooks.register [:posts, :pages], :post_render do |doc|
  next unless doc.output_ext == '.html'

  ImageDimensionsHook.inject_dimensions(doc)
end
