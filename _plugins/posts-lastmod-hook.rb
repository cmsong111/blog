#!/usr/bin/env ruby
# frozen_string_literal: true

# _plugins/posts-lastmod-hook.rb
#
# Populates `last_modified_at` for all posts using a single `git log` invocation
# per build instead of spawning 2 git subprocesses per post (~376 spawns for 188 posts).

require 'open3'

Jekyll::Hooks.register :site, :post_read do |site|
  cmd = [
    'git', '-c', 'core.quotepath=false',
    'log', '--format=COMMIT:%ad', '--date=iso', '--name-only',
    'HEAD', '--', '_posts'
  ]

  stdout, status = Open3.capture2(*cmd, chdir: site.source)
  next unless status.success? && !stdout.empty?

  commit_counts = Hash.new(0)
  latest_dates = {}
  current_date = nil

  stdout.each_line do |raw_line|
    line = raw_line.strip
    next if line.empty?

    if line.start_with?('COMMIT:')
      current_date = line.delete_prefix('COMMIT:').strip
    elsif current_date
      commit_counts[line] += 1
      latest_dates[line] ||= current_date
    end
  end

  site.posts.docs.each do |post|
    rel_path = post.relative_path
    if commit_counts[rel_path] > 1 && latest_dates[rel_path]
      post.data['last_modified_at'] = latest_dates[rel_path]
    end
  end
end
