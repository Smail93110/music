setInterval(() => {
    fetch('/votes').then(res => res.json()).then(data => {
      data.forEach(song => {
        console.log(`${song.title}: ${song.votes} votes`);
        // Ici tu peux mettre à jour dynamiquement les votes dans la page
      });
  
      // Gestion égalité (exemple simple)
      const votes = data.map(song => song.votes);
      const maxVote = Math.max(...votes);
      const isTie = votes.filter(v => v === maxVote).length > 1;
  
      if(isTie){
        console.log("Égalité détectée !");
        // Afficher phrase égalité dans ta page
      } else {
        // Retirer phrase égalité si elle existe
      }
    });
  }, 5000);
  