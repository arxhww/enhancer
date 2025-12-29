from infra.recovery.detector import scan

zombies = scan()
print([z.as_dict() for z in zombies])
