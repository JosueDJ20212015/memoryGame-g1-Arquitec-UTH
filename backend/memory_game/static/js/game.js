// static/js/game.js
// Control principal del tablero del juego de memoria (versión actual)

document.addEventListener("DOMContentLoaded", () => {
    const cards = document.querySelectorAll(".card");

    // Asigna evento a cada carta
    cards.forEach((card, index) => {
        card.addEventListener("click", () => handleCardClick(index));
    });
});

function handleCardClick(pos) {
    fetch(`/game/reveal/${pos}/`)
        .then(response => response.json())
        .then(data => {
            if (!data || !data.estado_partida) return;

            console.log("🧠 Respuesta del servidor:", data);

            // Actualizar las cartas según su estado
            updateCards(data.estado_partida.cartas);

            // Si no fue acierto, girar hacia atrás después de 1s
            if (data.status === "checked" && !data.acierto) {
                setTimeout(() => {
                    updateCards(data.estado_partida.cartas);
                }, 1000);
            }

            // Mostrar estadísticas básicas
            document.getElementById("moves")?.textContent = data.estado_partida.movimientos;
            document.getElementById("matches")?.textContent = data.estado_partida.aciertos;
        })
        .catch(error => console.error("❌ Error en fetch:", error));
}

function updateCards(cardsData) {
    cardsData.forEach(c => {
        const cardDiv = document.querySelector(`.card[data-pos="${c.posicion}"]`);
        if (!cardDiv) return;

        if (c.emparejada || c.revelada) {
            // Mostrar el emoji
            cardDiv.classList.add("flipped");
            cardDiv.innerHTML = `<div class="emoji">${c.valor}</div>`;
        } else {
            // Mostrar dorso
            cardDiv.classList.remove("flipped");
            cardDiv.innerHTML = "";
        }
    });
}
