# frozen_string_literal: true

# _plugins/seo-sitemap-hook.rb
#
# Excludes thin tag archive pages (/tags/<tag>/) and paginated listing pages (/page2+/)
# from sitemap.xml and marks them `noindex: true` so search engines focus crawl budget
# on posts, categories, and core tabs while still following internal links.

Jekyll::Hooks.register :site, :pre_render do |site|
  site.pages.each do |page|
    is_tag_archive = page.data['layout'] == 'tag'
    is_paginated_page = page.url.match?(%r{^/page\d+/})

    if is_tag_archive || is_paginated_page
      page.data['sitemap'] = false
      page.data['noindex'] = true
    end
  end
end
