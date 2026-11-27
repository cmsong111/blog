#!/usr/bin/env bash
#
# Run jekyll serve and then launch the site

prod=false
incremental=true
command="bundle exec jekyll s -l"
host="127.0.0.1"

help() {
  echo "Usage:"
  echo
  echo "   bash /path/to/run [options]"
  echo
  echo "Options:"
  echo "     -H, --host [HOST]    Host to bind to."
  echo "     -p, --production     Run Jekyll in 'production' mode."
  echo "     -f, --full           Disable incremental rebuild."
  echo "     -h, --help           Print this help information."
}

while (($#)); do
  opt="$1"
  case $opt in
  -H | --host)
    host="$2"
    shift 2
    ;;
  -p | --production)
    prod=true
    shift
    ;;
  -f | --full)
    incremental=false
    shift
    ;;
  -h | --help)
    help
    exit 0
    ;;
  *)
    echo -e "> Unknown option: '$opt'\n"
    help
    exit 1
    ;;
  esac
done

command="$command -H $host"

if $incremental; then
  command="$command --incremental"
fi

if $prod; then
  command="JEKYLL_ENV=production $command"
fi

if [ -f /.dockerenv ]; then
  # Write generated files to container-local ext4 instead of host bind-mount for faster I/O
  command="$command -d /tmp/_site"
fi

if [ -e /proc/1/cgroup ] && grep -q docker /proc/1/cgroup; then
  command="$command --force_polling"
fi

echo -e "\n> $command\n"
eval "$command"
