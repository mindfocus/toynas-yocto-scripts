#!/bin/bash

# Usage:
# ./build-device-type-json.sh [directory]
# this generates device-type-slug.json in the root of the balena-<board> directory
# the directory can be passed as an optional argument, default is 2 levels higher than the script itself

echo "Building JSON manifest..."

cd `dirname $0`
mydir=`pwd -P`
echo $mydir
rootdir=${1:-$mydir/../../}

function quit {
    rm -f "$slug".json
    echo $0: $1 >&2
    exit 1
}

npm install --production --quiet || quit "ERROR - Please make sure the 'npm' package is installed and working before running this script."

which nodejs >/dev/null 2>&1 && NODE=nodejs || NODE=node
if [ ! -x "$(command -v $NODE)" ]; then
    quit "ERROR - Please install the 'nodejs' package before running this script."
fi
echo `dirname $0`
cd $rootdir
rm -f *.json

for filename in *.coffee; do
    slug="${filename%.*}"
{ NODE_PATH=$mydir/node_modules $NODE > "$slug".json << EOF
    require('coffeescript/register');
    var dt = require('@resin.io/device-types');
    var manifest = require('./${filename}');
    var slug = '${slug}';
    var builtManifest = dt.buildManifest(manifest, slug);
    console.log(JSON.stringify(builtManifest, null, '\t'));
EOF
}

if [ ! -s "$slug".json ]; then
    quit "ERROR - Please check your nodejs installation. The '$NODE' binary did not generate a proper .json."
fi
done

echo "...Done"
