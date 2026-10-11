# frozen_string_literal: true

# _plugins/category-folder-hook.rb
#
# Automatically populates post categories directly from the directory structure under `_posts/`.
# The folder names on disk are the Single Source of Truth for category names.
#
# Examples:
#   _posts/Spring/Feature/post.md          => categories: ["Spring", "Feature"]
#   _posts/Spring/AI/post.md               => categories: ["Spring", "AI"]
#   _posts/Spring/Wanted-Challenge/post.md => categories: ["Spring", "Wanted-Challenge"]
#   _posts/Java/Swing/post.md              => categories: ["Java", "Swing"]
#   _posts/Blog/Jekyll/post.md             => categories: ["Blog", "Jekyll"]
#   _posts/Dev/Book/post.md                => categories: ["Dev", "Book"]
#   _posts/Dev/post.md                     => categories: ["Dev"]

Jekyll::Hooks.register :site, :post_read do |site|
  site.posts.docs.each do |post|
    rel_path = post.relative_path.sub(%r{^_posts/}, '')
    subdirs = rel_path.split('/')[0...-1]

    # Subdirectories directly dictate post categories as-is
    unless subdirs.empty?
      post.data['categories'] = subdirs
    end
  end
end
