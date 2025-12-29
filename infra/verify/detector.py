from infra.verify.manager import VerifyManager

def run_verification():
    vm = VerifyManager()
    return vm.verify_all()
