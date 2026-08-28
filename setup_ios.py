#!/usr/bin/env python3
"""
Lumiere Coaching - iOS/Xcode kurulum betiği

Bu betik, Capacitor tabanlı projeyi Xcode'da açmak için gereken adımları
otomatik olarak yapar:

  1. npm bağımlılıklarını kurar         (npm install)
  2. Web uygulamasını derler             (npm run build -> dist/)
  3. iOS platform klasörünü oluşturur   (npx cap add ios)
  4. Web çıktısını iOS'a kopyalar       (npx cap sync ios)
  5. Xcode'da projeyi açar              (npx cap open ios)

NOT: 5. adım (Xcode) yalnızca macOS üzerinde çalışır. Linux/Windows'ta
      önceki hazırlık adımları tamamlanır ve bir uyarı gösterilir.
"""

import os
import shutil
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))


def run(command, check=True):
    """Verilen komutu çalıştırır ve çıktısını ekrana basar."""
    print(f"\n$ {command}")
    result = subprocess.run(command, cwd=ROOT, shell=True)
    if check and result.returncode != 0:
        print(f"\n[!] Komut hata ile bitti (kod {result.returncode}): {command}")
        sys.exit(result.returncode)
    return result.returncode


def main():
    print("=== Lumiere Coaching iOS/Xcode Kurulumu ===")

    # 1) npm install
    run("npm install")

    # 2) Web build (dist/ klasörünü oluşturur - cap sync bunu kullanır)
    run("npm run build")

    # 3) iOS platform klasörü
    ios_dir = os.path.join(ROOT, "ios")
    if not os.path.isdir(ios_dir):
        print("\n[i] 'ios/' klasörü bulunamadı, Capacitor ile ekleniyor...")
        returncode = run("npx cap add ios", check=False)
        if returncode != 0:
            print("\n[!] 'npx cap add ios' hata verdi.")
            if shutil.which("pod") is None:
                print(
                    "    CocoaPods kurulu görünmüyor. macOS'te şunlardan biriyle kurun:\n"
                    "      sudo gem install cocoapods\n"
                    "      brew install cocoapods\n"
                    "    Ardından bu betiği tekrar çalıştırın."
                )
            sys.exit(1)
    else:
        print("\n[i] 'ios/' klasörü zaten mevcut, atlanıyor.")

    # 4) Web çıktısını iOS projesine senkronize et
    run("npx cap sync ios")

    # 5) Xcode'da aç
    if sys.platform == "darwin":
        run("npx cap open ios")
    else:
        print(
            "\n[!] Bu ortam macOS değil, Xcode burada açılamaz.\n"
            "    Hazırlık tamamlandı. Projeyi kendi Mac'inizde şu komutla açın:\n"
            "      cd <proje-dizini> && npx cap open ios\n"
            "    veya 'ios/App/App.xcodeproj' dosyasını çift tıklayın."
        )

    print("\n=== Kurulum tamamlandı ===")


if __name__ == "__main__":
    main()
