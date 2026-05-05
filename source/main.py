from nmap_scan import run, info

def main():
    # info()
    run(target="192.168.0.1", ports_to_scan="22,80,1900")


if __name__ == "__main__":
    main()