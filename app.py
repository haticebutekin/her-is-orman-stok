<script src="https://unpkg.com/html5-qrcode"></script>

<script>
let aktif = false;

function kamera(){
    if(aktif) return;
    aktif = true;

    const scanner = new Html5Qrcode("kamera");

    scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 250 },
        (text) => {

            // 🔊 bip sesi
            let beep = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
            beep.play();

            // barkodu inputa yaz
            document.getElementById("barkod").value = text;

            // otomatik gönder (satış)
            document.forms[0].submit();
        }
    );
}
</script>
