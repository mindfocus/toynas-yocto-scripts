#!/usr/bin/env python3

import sys, os, re, contextlib, yaml, tempfile, git, logging, time, urllib.request, json
from getopt import getopt
from getopt import GetoptError
from subprocess import Popen,PIPE

logger = logging.getLogger()

repo_list = [
    "git@github.com:balena-os/balena-bepmarine.git",
    "git@github.com:balena-os/balena-ts.git",
    "git@github.com:balena-os/balena-raspberrypi.git",
    "git@github.com:balena-os/balena-edison.git",
    "git@github.com:balena-os/balena-fastenal-bbb.git",
    "git@github.com:balena-os/balena-fsl-arm.git",
    "git@github.com:balena-os/balena-intel.git",
    "git@github.com:balena-os/balena-jetson-j120-tx2.git",
    "git@github.com:balena-os/balena-nanopc-t4.git",
    "git@github.com:balena-os/balena-odroid.git",
    "git@github.com:balena-os/balena-beaglebone.git",
    "git@github.com:balena-os/balena-qemu.git",
    "git@github.com:balena-os/balena-up-board.git",
    "git@github.com:balena-os/balena-variscite.git",
    "git@github.com:balena-os/balena-dt-cloudconnector.git",
    "git@github.com:balena-os/balena-allwinner.git",
    "git@github.com:balena-os/balena-jetson.git",
    "git@github.com:balena-os/balena-jetson-skx2.git",
    "git@github.com:balena-os/balena-val100.git",
    "git@github.com:balena-os/balena-alliance-raspberrypi3.git",
    "git@github.com:balena-os/balena-stem-x86-32bit.git",
    "git@github.com:balena-os/balena-technexion.git",
    "git@github.com:balena-os/balena-variscite-mx8.git",
    "git@github.com:balena-os/balena-xilinx.git",
    "git@github.com:balena-os/balena-asus-tinker-board.git",
    "git@github.com:balena-os/balena-compulab.git",
    "git@github.com:balena-os/balena-coral.git",
    "git@github.com:balena-os/balena-rockchip-rk3288.git",
    "git@github.com:balena-os/balena-jetson-srd3.git",
    "git@github.com:balena-os/balena-jetson-wnb.git",
]

def main(argv):
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    lf = logging.FileHandler(os.path.basename(__file__) + str(int(time.time())) + '.log')
    lf.setLevel(logging.DEBUG)
    lf.setFormatter(formatter)
    logger.addHandler(lf)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    try:
        opts, args = getopt(argv[1:], "he:b:p:k", ["help", "esr-version=", "bos-version=", "path=", "keep-tmp-dir="])
    except GetoptError as ex:
        logger.error("get opt error: %s" % (str(ex)))
        usage()

    arg_dict = {}
    arg_dict["path"] = None
    arg_dict["keepTmpDir"] = False
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-e", "--esr-version"):
            arg_dict["esrVersion"] = str(a)
        elif o in ("-b", "--bos-version"):
            arg_dict["bOSVersion"] = str(a)
        elif o in ("-p", "--path"):
            arg_dict["path"] = str(a)
        elif o in ("-k", "--keep-tmp-dir"):
            arg_dict["keepTmpDir"] = True
        else:
            assert False, "unhandled option"

    try:
        if arg_dict['esrVersion'] == None or arg_dict['bOSVersion'] == None:
            logger.error ("Both --esr-version and --bos-version are required")
            usage()
    except KeyError:
        usage()
        pass

    if arg_dict['keepTmpDir'] == True:
        tmpDir = tempfile.mkdtemp()
        esr_device_list = create_esr_branches(tmpDir, arg_dict)
    else:
        with tempfile.TemporaryDirectory() as tmpDir:
            esr_device_list = create_esr_branches(tmpDir, arg_dict)

    missing = False
    canonical_device_list = device_list()
    for device in canonical_device_list:
        if device in esr_device_list:
            # TODO build_and_deploy(device, esr-release-branch, deploy-environment, jenkins-user, jenkins-password)
            continue
        else:
            missing = True
            logger.error ("Missing " + device + " from ESR branches")
    if missing == False:
        logger.info ("All canonical devices have an" + arg_dict["esrVersion"] + "  ESR branch now.")

def build_and_deploy(device, esr-release-branch, deploy-environment, jenkins-user, jenkins-password):
    # TODO trigger jenkin jobs
    # Jenkins currently hides behind an OAuthProxy that authenticates with github
    # We need to fetch the cookie from the request headers left from accessing https://jenkins.dev.resin.io/login
    # curl --cookie "${_cookie}" -X POST -L --user ${username}:${jenkinsAPIToken} https://jenkins.dev.resin.io/job/balenaOS-deploy-ESR/buildWithParameters \
    # --data board=${device} --data tag=${esr-release-branch} --data deployTo=${deploy-environment}
    # This jenkins Python library does not support authenticating with a cookie
    import jenkins
    j = jenkins.Jenkins("https://jenkins.dev.resin.io", username=jenkins-user, password=jenkins-password)
    params = { 'board':device, 'tag':esr-release-branch, 'deployTo':deploy-environment}
    j.build_job('balenaOS-deploy-ESR', params)
    return

def build_device_types_json():
    process = Popen("./balena-yocto-scripts/build/build-device-type-json.sh", stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()

def get_slugs_from_device_types(device_list):
    files = []
    build_device_types_json()
    files += [each for each in os.listdir(os.getcwd()) if each.endswith(".json")]
    for f in files:
        with open(f, "r") as fd:
            jobj = json.load(fd)
            device_list.append(jobj['slug'])

def esr_branch_exists(remote, device_esr_branch):
    process = Popen(['git', 'ls-remote', '--heads', remote, device_esr_branch], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if stdout:
        return True
    else:
        log.debug("No ls-remote match: " + stderr)
        return False

def create_esr_branches(tmpDir, arg_dict):
    esr_device_list = []
    os.chdir(tmpDir)
    logger.info ("Working in " + os.getcwd())
    for repourl in repo_list:
        repourl = repourl.rstrip()
        (year, month, build) = arg_dict['esrVersion'].split(".")
        device_esr_branch = year + '.' + month + '.x'
        if esr_branch_exists(repourl, device_esr_branch):
            logger.info ("ESR branch " + device_esr_branch + " already exists in " + repourl )
            continue
        repoDir = tmpDir + os.sep + os.path.splitext(os.path.basename(repourl))[0]
        clone(repourl, repoDir)

        with pushd(repoDir):
            get_slugs_from_device_types(esr_device_list)
            with pushd(os.getcwd() + os.sep + 'layers' + os.sep + 'meta-balena'):
                if not os.path.isfile(os.getcwd() + os.sep + 'repo.yml'):
                    logger.error ("missing repo.yml in " + os.getcwd())
                    return false
                meta_balena_esr_branch = arg_dict["bOSVersion"] + '.x'
                branch_or_checkout(meta_balena_esr_branch)
            branch_or_checkout(device_esr_branch)
            apply_esr_changes(arg_dict)
            with pushd(os.getcwd() + os.sep + 'layers' + os.sep + 'meta-balena'):
                if not os.path.isfile(os.getcwd() + os.sep + 'repo.yml'):
                    logger.error ("missing repo.yml in " + os.getcwd())
                    return false
                try:
                    commit("Declare ESR " + arg_dict['bOSVersion'])
                except git.exc.GitCommandError as e:
                    logger.info ("Commit did not happen - already up to date.")
                    logger.debug(e)
                    pass
                push('origin', meta_balena_esr_branch)
            commit("Declare ESR " + year + '.' + month)
            push('origin', device_esr_branch)
    return esr_device_list

def clone(repourl, destDir):
    if not os.path.exists(destDir):
        os.mkdir(destDir)
    logger.info ("Cloning " + repourl + " into " + destDir)
    repo = git.Repo.clone_from(repourl, destDir)
    reader = repo.config_reader()
    signature = reader.get_value("user", "email")
    for submodule in repo.submodules:
        submodule.update(init=True)
    return True

def branch_or_checkout(name):
    repo = git.Repo(os.getcwd())
    try:
        logger.info ("Checking out " + name)
        repo.git.checkout('-b', name, "origin/" + name)
    except:
        logger.info ("Branching " + name)
        repo.create_head(name)
        repo.heads[name].checkout()
    return True

def commit(message):
    repo = git.Repo(os.getcwd())
    reader = repo.config_reader()
    name = reader.get_value("user", "name")
    email = reader.get_value("user", "email")
    repo.git.add(".")
    logger.info ("Commiting " + message)
    repo.git.commit('-m', message, '-m', 'Change-type: none')
    return True

def push(remote, branch):
    logger.info ("Pushing " + branch + " to " + remote)
    repo = git.Repo(os.getcwd())
    origin = repo.remote(name=remote)
    try:
        repo.git.push(origin, branch)
    except git.exc.GitCommandError as e:
        logger.warn("Did not push " + branch + "- maybe exists already?")
        logger.debug(e)
        return False
    return True

def apply_esr_changes(arg_dict):
    try:
        if arg_dict["path"] == None:
            arg_dict["path"] = "."
        thispath = arg_dict["path"]
        if ( not os.path.isfile(thispath + os.sep + 'VERSION') or
             not os.path.isfile(thispath + os.sep + 'CHANGELOG.md') or
             not os.path.isfile(thispath + os.sep + 'repo.yml')):
            logger.error ("Not a device repository")
            return False

        # Change into the meta-balena directory
        with pushd(thispath + os.sep + 'layers' + os.sep + 'meta-balena'):
            if not os.path.isfile(thispath + os.sep + 'repo.yml'):
                logger.error ("Missing repo.yml in " + os.getcwd())
                return False
            yaml_modify_repo(thispath + os.sep + 'repo.yml', arg_dict["bOSVersion"], arg_dict["esrVersion"])

        if yaml_modify_repo(thispath + os.sep + 'repo.yml', None, arg_dict["esrVersion"]):
            if Modify_ESR_version(thispath + os.sep + 'VERSION', arg_dict["esrVersion"]):
                Modify_ESR_changelog(thispath + os.sep + 'CHANGELOG.md', arg_dict["esrVersion"])
        else:
            logger.warn ("ESR version already defined")
    except KeyError:
        logger.error ("Both --esr-version and --bos-version are required")
        usage()
        pass

@contextlib.contextmanager
def pushd(ndir):
        pdir = os.getcwd()
        os.chdir(ndir)
        try:
                yield
        finally:
                os.chdir(pdir)

def usage():
    print ("Usage: " + script_name + " [OPTIONS]\n")
    print ("\t-h Display usage")
    print ("\t-e ESR version (e.g 2020.07.1)")
    print ("\t-b BalenaOS version (e.g 2.68)\n")
    sys.exit(1)


def check_esr_version(version):
    pattern = re.compile("^[1-3][0-9]{3}\.[0-1][0-9]\.[0-9]$")
    if not pattern.match(version):
        return False
    return True

def check_bsp_branch(branch):
    pattern = re.compile("^[1-3][0-9]{3}\.[0-1][0-9]\.x$")
    if not pattern.match(branch):
        logger.info ("Invalid branch pattern " + branch)
        return False
    return True

def check_bos_version(version):
    pattern = re.compile("^[0-9]+\.[0-9]+$")
    if not pattern.match(version):
        return False
    return True

def yaml_modify_repo(filePath="./repo.yml", bosVersion="", esrVersion=""):
    if esrVersion != None:
        if not check_esr_version(esrVersion):
            logger.info ("Invalid ESR version " + esrVersion)
            return False
        (year, month, build) = esrVersion.split(".")

    with open(filePath, 'r') as original: ydata = yaml.safe_load(original)
    original.close()

    if 'esr' in ydata:
        # Silent return
        return False

    if bosVersion != None:
        # Modifying meta-balena
        if not check_bos_version(bosVersion):
            logger.info ("Invalid balenaOS version " + bosVersion)
            return False
        branch = year + "." + month + ".x"
        if not check_bsp_branch(branch):
            return False
        ydata['esr'] =  { 'version': bosVersion, 'bsp-branch-pattern': branch }
    else:
        # Modifying device repository
        ydata['esr'] =  { 'version': year + '.' + month }

    with open(filePath, 'w') as modified: yaml.dump(ydata, modified)
    modified.close()

    return True

def Modify_ESR_changelog(filePath="./CHANGELOG.md", esrVersion=""):
    if not check_esr_version(esrVersion):
        logger.info ("Invalid ESR version: " + esrVersion)
        return False
    with open(filePath, 'r') as original: data = original.read()
    original.close()
    with open(filePath, 'w') as modified: modified.write("# " + esrVersion + "\n## (" + esrVersion + ")\n\nDeclare ESR " + esrVersion + "\n\n" + data)
    modified.close()
    return True

def Modify_ESR_version(filePath="./VERSION", esrVersion=""):
    if not check_esr_version(esrVersion):
        logger.info ("Invalid ESR version: " + esrVersion)
        return False
    with open(filePath, 'r') as original: data = original.read()
    original.close()
    (data, count) = re.subn("^\d+\.\d+.\d+\+rev\d+$", esrVersion, data)
    if count != 1:
        logger.error ("Error in VERSION file")
        return False
    with open(filePath, 'w') as modified:  modified.write(data)
    modified.close()
    return True

def device_list():
    device_list = []
    apiEnv = "balena-cloud.com/"
    translation = "v6"
    url = "https://api." + apiEnv + translation + "/device_type?$select=slug"
    raw = urllib.request.urlopen(url)
    json_obj = json.load(raw)
    for e in json_obj['d']:
        device_list.append(e['slug'])
    return device_list

if __name__ == '__main__':
    script_name = sys.argv[0]
    main(sys.argv)
