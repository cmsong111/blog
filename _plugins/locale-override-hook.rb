# frozen_string_literal: true

# _plugins/locale-override-hook.rb
#
# Overrides selected Chirpy locale labels in-memory without copying the entire
# theme `_data/locales/*.yml` file, keeping theme upgrades safe and clean.

Jekyll::Hooks.register :site, :post_read do |site|
  locales = site.data['locales']
  next unless locales.is_a?(Hash)

  locales.each_value do |locale|
    next unless locale.is_a?(Hash) && locale['post'].is_a?(Hash)

    locale['post']['relate_posts'] = '함께 읽으면 좋은 글'
  end
end
