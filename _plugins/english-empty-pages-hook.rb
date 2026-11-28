# frozen_string_literal: true

Jekyll::Hooks.register :site, :pre_render do |site|
  next unless site.config['lang'] == 'en' && site.posts.docs.empty?

  # Keep page.layout for Chirpy navigation and titles while replacing its empty listing.
  empty_layout = site.layouts.fetch('english-empty')
  %w[home archives categories tags].each do |layout_name|
    site.layouts[layout_name] = empty_layout
  end
end
