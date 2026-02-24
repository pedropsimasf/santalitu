(function () {
  'use strict';

  // ===== STATE =====
  let currentDate = new Date();
  let liturgyData = null;
  let currentMode = 'missa'; // missa | leituras | devocao

  const $ = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);

  const MONTHS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  const WEEKDAYS = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'];

  function fmtBR(d) { return `${WEEKDAYS[d.getDay()]}, ${d.getDate()} de ${MONTHS[d.getMonth()]} de ${d.getFullYear()}`; }
  function fmtAPI(d) { return `${String(d.getDate()).padStart(2, '0')}-${String(d.getMonth() + 1).padStart(2, '0')}-${d.getFullYear()}`; }
  function fmtISO(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }

  const LIT_COLORS = {
    'verde': { hex: '#2d5a27', label: 'Verde' },
    'roxo': { hex: '#5b2d8e', label: 'Roxo' },
    'branco': { hex: '#b8a88a', label: 'Branco' },
    'vermelho': { hex: '#c0392b', label: 'Vermelho' },
    'rosa': { hex: '#c0506a', label: 'Rosa' },
  };

  function getEvangelista(ref) {
    if (!ref) return 'São Mateus';
    const r = ref.toLowerCase();
    if (r.startsWith('mt')) return 'São Mateus';
    if (r.startsWith('mc')) return 'São Marcos';
    if (r.startsWith('lc')) return 'São Lucas';
    if (r.startsWith('jo')) return 'São João';
    return 'São Mateus';
  }

  function isQuaresma(d) {
    if (!d) return false;
    return (d.liturgia || '').toLowerCase().includes('quaresma') || ((d.cor || '').toLowerCase() === 'roxo');
  }

  function isDomingo(d) {
    if (!d) return false;
    return (d.liturgia || '').toLowerCase().includes('domingo') || currentDate.getDay() === 0;
  }

  function shouldShowGloria(d) {
    if (!d) return false;
    const lit = (d.liturgia || '').toLowerCase();
    if (lit.includes('solenidade') || lit.includes('natal') || lit.includes('pentecostes')) return true;
    if (lit.includes('quaresma') || lit.includes('advento')) return false;
    if (lit.includes('domingo') || currentDate.getDay() === 0) return true;
    if (lit.includes('festa')) return true;
    return false;
  }

  const MEMORIAL = [
    'Anunciamos, Senhor, a vossa morte e proclamamos a vossa ressurreição. Vinde, Senhor Jesus!',
    'Todas as vezes que comemos deste pão e bebemos deste cálice, anunciamos, Senhor, a vossa morte, enquanto esperamos a vossa vinda!',
    'Salvador do mundo, salvai-nos, vós que nos libertastes pela cruz e ressurreição!'
  ];

  // ===== PRECES (Oração dos Fiéis) =====

  // Tenta buscar preces do JSON gerado pelo crawler
  async function fetchPrecesJSON(date) {
    const iso = fmtISO(date);
    const cacheKey = `preces_${iso}`;
    console.log('[fetchPrecesJSON] Data:', iso, '| Cache key:', cacheKey);

    // 1. Tentar arquivo local preces_data/
    try {
      const r = await fetch(`preces_data/preces_${iso}.json`, { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        const data = await r.json();
        console.log('[fetchPrecesJSON] ✓ Arquivo local carregado:', iso, '| OE:', data.oracao_eucaristica);
        try { localStorage.setItem(cacheKey, JSON.stringify(data)); } catch (e) { }
        return data;
      }
    } catch (e) {
      console.warn('[fetchPrecesJSON] ✗ Erro ao buscar arquivo local:', iso, e.message);
    }

    // 2. Tentar API do preces_server.py
    try {
      const r = await fetch(`http://127.0.0.1:8082/preces/${iso}`, { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        const data = await r.json();
        if (!data.error) {
          console.log('[fetchPrecesJSON] ✓ API retornou:', iso, '| OE:', data.oracao_eucaristica);
          try { localStorage.setItem(cacheKey, JSON.stringify(data)); } catch (e) { }
          return data;
        }
      }
    } catch (e) {
      console.warn('[fetchPrecesJSON] ✗ Erro ao buscar API:', iso, e.message);
    }

    // 3. Cache local
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const data = JSON.parse(cached);
        console.log('[fetchPrecesJSON] ✓ Retornado do localStorage:', iso, '| OE:', data.oracao_eucaristica);
        return data;
      }
    } catch (e) {
      console.warn('[fetchPrecesJSON] ✗ Erro ao ler cache localStorage:', e.message);
    }

    console.warn('[fetchPrecesJSON] ✗ Nenhum JSON encontrado para:', iso);
    return null;
  }

  // Renderiza preces a partir do JSON do crawler
  function renderPrecesFromJSON(precesData) {
    let html = '<div class="dialogue"><span class="label-p">P.</span> Irmãos e irmãs, elevemos a Deus as nossas preces, confiando na sua bondade e misericórdia.</div>';

    // Resposta destacada
    if (precesData.resposta) {
      html += `<div class="refrain" style="margin:0.6rem 0;">♦ ${precesData.resposta}</div>`;
    }

    // Intenções
    if (precesData.intencoes && precesData.intencoes.length > 0) {
      precesData.intencoes.forEach(int => {
        html += `<div class="dialogue"><span class="label-p">L.</span> ${int.texto}</div>`;
        html += `<div class="response"><strong>T. ${precesData.resposta || 'Senhor, escutai a nossa prece.'}</strong></div>`;
      });
    }

    html += '<div class="separator"></div>';
    html += '<div class="dialogue"><span class="label-p">P.</span> Ó Deus, nosso Pai, que escutais os apelos dos vossos filhos, acolhei as preces que vos dirigimos e concedei-nos o que vos pedimos com fé. Por Cristo, nosso Senhor.</div>';
    html += '<div class="response"><strong>T. Amém.</strong></div>';

    // Fonte
    if (precesData.fonte && precesData.fonte !== 'gerado_automatico') {
      html += `<div class="liturgical-note" style="margin-top:0.6rem;"><strong>Fonte:</strong> ${precesData.fonte}</div>`;
    }

    return html;
  }

  // Fallback: gera preces inline baseadas na estação litúrgica
  function getPrecesFallback(data) {
    if (!data) return '';
    const lit = (data.liturgia || '').toLowerCase();
    let intencoesEspecificas = '';

    if (lit.includes('quaresma')) {
      intencoesEspecificas = `
        <div class="dialogue"><span class="label-p">L.</span> Pelo Papa, pelos bispos e por todo o clero: para que sejam sustentados pela Palavra de Deus e conduzam o povo com fidelidade neste tempo de conversão. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Pelos governantes e por todos os que exercem autoridade: para que promovam a justiça, a paz e o bem comum, especialmente para os mais pobres e necessitados. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Pelos catecúmenos e por todos os que se preparam para celebrar a Páscoa: para que sejam conduzidos pela Palavra e pelo Espírito e recebam a graça de vencer as tentações. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Pela nossa comunidade e por todas as famílias: para que a vivência da Campanha da Fraternidade nos leve a superar a indiferença e a abrir o coração aos irmãos mais necessitados. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Por todos nós aqui reunidos: para que, seguindo o exemplo de Cristo no deserto, saibamos resistir às tentações pela oração, pelo jejum e pela caridade. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
      `;
    } else {
      intencoesEspecificas = `
        <div class="dialogue"><span class="label-p">L.</span> Pela Santa Igreja de Deus, pelo Papa e por todos os pastores: para que, guiados pelo Espírito Santo, sejam sempre fiéis à missão de anunciar o Evangelho. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Pelos governantes e por todos os que exercem autoridade: para que promovam a justiça, a paz e o bem comum. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Pelos que sofrem, pelos doentes, pelos que perderam entes queridos e por todos os necessitados: para que encontrem no Senhor consolo e esperança. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Por nossa comunidade: para que vivamos na fé, na caridade e na comunhão fraterna. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
        <div class="dialogue"><span class="label-p">L.</span> Por todos nós aqui reunidos: para que esta celebração eucarística nos fortaleça no caminho da santidade e do serviço ao próximo. Rezemos ao Senhor.</div>
        <div class="response"><strong>T. Senhor, escutai a nossa prece.</strong></div>
      `;
    }

    return `
      <div class="dialogue"><span class="label-p">P.</span> Irmãos e irmãs, elevemos a Deus as nossas preces, confiando na sua bondade e misericórdia.</div>
      ${intencoesEspecificas}
      <div class="separator"></div>
      <div class="dialogue"><span class="label-p">P.</span> Ó Deus, nosso Pai, que escutais os apelos dos vossos filhos, acolhei as preces que vos dirigimos e concedei-nos o que vos pedimos com fé. Por Cristo, nosso Senhor.</div>
      <div class="response"><strong>T. Amém.</strong></div>
    `;
  }

  // Carrega preces: tenta JSON do crawler, senão gera inline
  async function loadPreces(data) {
    const el = $('#precesContent');
    console.log('[loadPreces] Iniciando... data ISO:', fmtISO(currentDate));
    
    // Tenta carregar do crawler JSON
    const precesJSON = await fetchPrecesJSON(currentDate);
    console.log('[loadPreces] fetchPrecesJSON retornou:', precesJSON ? 'dados' : 'null');
    
    if (precesJSON && precesJSON.resposta && precesJSON.intencoes) {
      el.innerHTML = renderPrecesFromJSON(precesJSON);
      console.log('[loadPreces] ✓ Preces carregadas do JSON | Fonte:', precesJSON.fonte || 'cache', '| OE especificada:', precesJSON.oracao_eucaristica);
      
      // Atualizar Oração Eucarística se especificada no JSON
      if (precesJSON.oracao_eucaristica) {
        console.log('[loadPreces] ➤ Chamando setOracaoEucaristica com:', precesJSON.oracao_eucaristica);
        setOracaoEucaristica(precesJSON.oracao_eucaristica);
      } else {
        console.warn('[loadPreces] ⚠ JSON carregado mas SEM oracao_eucaristica!');
      }
      return;
    }
    
    // Fallback inline
    console.log('[loadPreces] ✗ JSON inválido ou incompleto, usando fallback inline');
    el.innerHTML = getPrecesFallback(data);
    
    // Default OE III para Quaresma, II para outros tempos
    const oeDefault = isQuaresma(currentDate) ? 'III' : 'II';
    console.log('[loadPreces] Fallback: setOracaoEucaristica com default:', oeDefault);
    setOracaoEucaristica(oeDefault);
  }

  // ===== ORAÇÃO EUCARÍSTICA DINÂMICA =====
  function setOracaoEucaristica(num) {
    const titulo = $('#oeTitulo');
    const content = $('#oeContent');
    console.log('[setOracaoEucaristica] Chamado com num:', num, '| tipo:', typeof num, '| titulo element:', titulo ? 'existe' : 'NÃO EXISTE', '| content element:', content ? 'existe' : 'NÃO EXISTE');
    
    if (!content) {
      // Se não existe container dinâmico, atualiza só o título
      console.log('[setOracaoEucaristica] ⚠ Sem container #oeContent, apenas atualizando título');
      if (titulo) {
        titulo.textContent = `Oração Eucarística ${num}`;
        console.log('[setOracaoEucaristica] Título atualizado para:', `Oração Eucarística ${num}`);
      }
      return;
    }
    
    if (titulo) {
      titulo.textContent = `Oração Eucarística ${num}`;
      console.log('[setOracaoEucaristica] ✓ Título atualizado para: Oração Eucarística', num);
    }
    
    content.innerHTML = getOracaoEucaristica(num);
    console.log('[setOracaoEucaristica] ✓ Conteúdo HTML atualizado para OE', num);
  }

  function getOracaoEucaristica(num) {
    const consagracao = `
      <div class="rubric">Narrativa da Instituição</div>
      <div class="dialogue"><span class="label-p">P.</span> Na noite em que ia ser entregue, Jesus tomou o pão,
        pronunciou a bênção de ação de graças, partiu e o deu a seus discípulos, dizendo:</div>
      <div class="consec-words">TOMAI, TODOS, E COMEI:<br>ISTO É O MEU CORPO,<br>QUE SERÁ ENTREGUE POR VÓS.</div>
      <div class="dialogue"><span class="label-p">P.</span> Do mesmo modo, no fim da Ceia, ele tomou o cálice em
        suas mãos, pronunciou a bênção de ação de graças, e o deu a seus discípulos, dizendo:</div>
      <div class="consec-words">TOMAI, TODOS, E BEBEI:<br>ESTE É O CÁLICE DO MEU SANGUE,<br>O SANGUE DA NOVA E ETERNA
        ALIANÇA,<br>QUE SERÁ DERRAMADO POR VÓS E POR TODOS<br>PARA REMISSÃO DOS PECADOS.<br><br><strong>FAZEI ISTO EM MEMÓRIA DE MIM.</strong></div>
      <div class="separator"></div>
      <div class="dialogue"><span class="label-p">P.</span> Eis o mistério da fé!</div>
      <div class="response"><strong>T. Anunciamos, Senhor, a vossa morte e proclamamos a vossa ressurreição. Vinde, Senhor Jesus!</strong></div>
      <div class="separator"></div>`;

    const doxologia = `
      <div class="separator"></div>
      <div class="dialogue"><span class="label-p">P.</span> Por Cristo, com Cristo, em Cristo, a vós, Deus Pai
        todo-poderoso, na unidade do Espírito Santo, toda a honra e toda a glória, agora e para sempre.</div>
      <div class="response" style="font-size:1.1em;"><strong>T. Amém!</strong></div>`;

    if (num === 'II') {
      return `
        <div class="dialogue"><span class="label-p">P.</span> Vós sois verdadeiramente Santo, ó Deus do
          universo, fonte de toda santidade. Santificai, pois, estas oferendas, derramando sobre elas o vosso
          Espírito, a fim de que se tornem para nós o Corpo e o Sangue de Jesus Cristo, nosso Senhor.</div>
        <div class="separator"></div>
        <div class="dialogue"><span class="label-p">P.</span> Estando para ser entregue e abraçando livremente a
          paixão, ele tomou o pão, deu graças, partiu-o e deu a seus discípulos, dizendo:</div>
        <div class="consec-words">TOMAI, TODOS, E COMEI:<br>ISTO É O MEU CORPO,<br>QUE SERÁ ENTREGUE POR VÓS.</div>
        <div class="dialogue"><span class="label-p">P.</span> Do mesmo modo, ao fim da Ceia, ele tomou o cálice, deu
          graças e o passou a seus discípulos, dizendo:</div>
        <div class="consec-words">TOMAI, TODOS, E BEBEI:<br>ESTE É O CÁLICE DO MEU SANGUE,<br>O SANGUE DA NOVA E ETERNA
          ALIANÇA,<br>QUE SERÁ DERRAMADO POR VÓS E POR TODOS<br>PARA REMISSÃO DOS PECADOS.<br><br><strong>FAZEI ISTO EM MEMÓRIA DE MIM.</strong></div>
        <div class="separator"></div>
        <div class="dialogue"><span class="label-p">P.</span> Eis o mistério da fé!</div>
        <div class="response"><strong>T. Anunciamos, Senhor, a vossa morte e proclamamos a vossa ressurreição. Vinde, Senhor Jesus!</strong></div>
        <div class="separator"></div>
        <div class="dialogue"><span class="label-p">P.</span> Celebrando, pois, a memória da morte e ressurreição
          do vosso Filho, nós vos oferecemos, ó Pai, o Pão da vida e o Cálice da salvação; e vos agradecemos
          porque nos tornastes dignos de estar aqui na vossa presença e vos servir.</div>
        <div class="dialogue"><span class="label-p">P.</span> E nós vos suplicamos que, participando do Corpo e do
          Sangue de Cristo, sejamos reunidos pelo Espírito Santo num só corpo.</div>
        <div class="dialogue"><span class="label-p">P.</span> Lembrai-vos, ó Pai, da vossa Igreja que se encontra
          dispersa por toda a terra e fazei-a crescer na caridade, com o nosso Papa, o nosso Bispo e todos
          os ministros do vosso povo.</div>
        <div class="dialogue"><span class="label-p">P.</span> Lembrai-vos também dos nossos irmãos e irmãs que
          morreram na esperança da ressurreição e de todos os que partiram desta vida. Acolhei-os junto a vós
          na luz da vossa face.</div>
        <div class="dialogue"><span class="label-p">P.</span> E nós vos suplicamos: tende piedade de todos nós e
          dai-nos participar da vida eterna, com a Virgem Maria, Mãe de Deus, São José, seu esposo, os santos
          Apóstolos e todos os que neste mundo viveram na vossa amizade. E assim possamos nós louvar-vos e
          glorificar-vos, por Jesus Cristo, vosso Filho.</div>
        ${doxologia}`;
    }

    if (num === 'IV') {
      return `
        <div class="dialogue"><span class="label-p">P.</span> Nós vos louvamos, Pai Santo, porque sois grande e
          porque fizestes todas as coisas com sabedoria e amor. Criastes o ser humano à vossa imagem e lhe
          confiastes o universo inteiro, para que, servindo a vós, seu Criador, dominasse toda criatura.</div>
        <div class="dialogue"><span class="label-p">P.</span> E quando, pela desobediência, perdeu a vossa
          amizade, não o abandonastes ao poder da morte, mas a todos socorrestes com bondade, para que,
          ao vos procurarem, pudessem encontrar-vos. Por muitas vezes oferecestes aos homens a vossa
          aliança e, pelos profetas, os ensinastes a esperar a salvação.</div>
        <div class="dialogue"><span class="label-p">P.</span> E tanto amastes o mundo, ó Pai, que, na plenitude dos
          tempos, enviastes o vosso Filho Unigênito para nos salvar. Ele se encarnou pelo Espírito Santo, nasceu
          da Virgem Maria e, em tudo semelhante a nós, exceto no pecado, anunciou aos pobres a salvação, aos
          cativos a liberdade, aos tristes a alegria.</div>
        <div class="dialogue"><span class="label-p">P.</span> Para realizar o vosso desígnio, entregou-se à morte
          e, ressuscitando, destruiu a morte e renovou a vida.</div>
        <div class="dialogue"><span class="label-p">P.</span> E, para que não vivamos mais para nós mesmos, mas
          para ele, que por nós morreu e ressuscitou, enviou de junto de vós, ó Pai, como primeiro dom para os
          que creem, o Espírito Santo, que, continuando no mundo a obra do vosso Filho, completasse toda
          santificação.</div>
        <div class="separator"></div>
        <div class="dialogue"><span class="label-p">P.</span> Santificai, pois, estas oferendas pelo vosso
          Espírito, a fim de que se tornem o Corpo e o Sangue de nosso Senhor Jesus Cristo, para a celebração
          deste grande mistério que ele nos deixou em sinal de aliança eterna.</div>
        ${consagracao}
        <div class="dialogue"><span class="label-p">P.</span> Celebrando agora, ó Pai, o memorial da nossa
          redenção, recordamos a morte de Cristo e a sua descida entre os mortos, proclamamos a sua ressurreição
          e ascensão à vossa direita; e, esperando a sua vinda gloriosa, nós vos oferecemos o seu Corpo e o seu
          Sangue, sacrifício do vosso agrado e salvação do mundo inteiro.</div>
        <div class="dialogue"><span class="label-p">P.</span> Olhai, ó Pai, para a oblação que apresentamos:
          é o próprio Cristo que se oferece e é oferecido; por este sacrifício, que ele vos é agradável, concedei
          que, alimentados pelo Corpo e Sangue do vosso Filho e repletos do seu Espírito Santo, nos tornemos
          em Cristo um só corpo e um só espírito.</div>
        <div class="dialogue"><span class="label-p">P.</span> Que o Espírito Santo faça de nós uma eterna
          oferenda para vós, para que alcancemos a herança eterna com os vossos eleitos: a Virgem Maria, Mãe
          de Deus, São José, seu esposo, os Apóstolos, os Mártires e todos os Santos, que imploram sem cessar
          a vossa misericórdia por nós.</div>
        <div class="dialogue"><span class="label-p">P.</span> Lembrai-vos, ó Pai, da vossa Igreja dispersa
          por toda a terra. Tornai-a perfeita na caridade, com o Papa, o nosso Bispo e todos os ministros.</div>
        <div class="dialogue"><span class="label-p">P.</span> Lembrai-vos também dos nossos irmãos e irmãs que
          morreram na paz de Cristo e de todos os mortos, cuja fé só vós conhecestes. Pai de bondade, fazei que
          todos os vossos filhos e filhas possam alcançar, com a Virgem Maria e todos os Santos, a herança
          eterna do vosso Reino, onde, com toda a criação enfim liberta do pecado e da morte, possamos
          glorificar-vos por Cristo, nosso Senhor, pelo qual distribuís ao mundo todo bem e toda graça.</div>
        ${doxologia}`;
    }

    // Default: OE III
    return `
      <div class="dialogue"><span class="label-p">P.</span> Na verdade, vós sois Santo, ó Deus do universo, e
        tudo o que criastes proclama o vosso louvor, porque, por Jesus Cristo, vosso Filho e Senhor nosso, e pela
        força do Espírito Santo, dais vida e santidade a todas as coisas e não cessais de reunir para vós um povo
        que vos ofereça em toda parte, do nascer ao pôr do sol, um sacrifício perfeito.</div>
      <div class="dialogue"><span class="label-p">P.</span> Por isso, ó Pai, nós vos suplicamos: santificai pelo
        Espírito Santo as oferendas que vos apresentamos para serem consagradas, a fim de que se tornem o Corpo
        e o Sangue de vosso Filho, nosso Senhor Jesus Cristo, que nos mandou celebrar estes mistérios.</div>
      <div class="response"><strong>T. Enviai o vosso Espírito Santo!</strong></div>
      <div class="separator"></div>
      ${consagracao}
      <div class="dialogue"><span class="label-p">P.</span> Celebrando agora, ó Pai, o memorial da paixão redentora
        do vosso Filho, da sua gloriosa ressurreição e ascensão ao céu, e enquanto esperamos sua nova vinda,
        nós vos oferecemos em ação de graças este sacrifício vivo e santo.</div>
      <div class="response"><strong>T. Aceitai, ó Senhor, a nossa oferta!</strong></div>
      <div class="dialogue"><span class="label-p">P.</span> Olhai com bondade a oblação da vossa Igreja e reconhecei
        nela o sacrifício que nos reconciliou convosco; concedei que, alimentando-nos com o Corpo e o Sangue do
        vosso Filho, repletos do Espírito Santo, nos tornemos em Cristo um só corpo e um só espírito.</div>
      <div class="response"><strong>T. O Espírito nos una num só corpo!</strong></div>
      <div class="dialogue"><span class="label-p">P.</span> Que o mesmo Espírito faça de nós uma eterna oferenda para
        alcançarmos a herança com os vossos eleitos: a santíssima Virgem Maria, Mãe de Deus, São José, seu
        esposo, os vossos santos Apóstolos e gloriosos Mártires, e todos os Santos, que não cessam de interceder
        por nós na vossa presença.</div>
      <div class="response"><strong>T. Fazei de nós uma perfeita oferenda!</strong></div>
      <div class="dialogue"><span class="label-p">P.</span> Nós vos suplicamos, Senhor, que este sacrifício da nossa
        reconciliação estenda a paz e a salvação ao mundo inteiro. Confirmai na fé e na caridade a vossa Igreja
        que caminha neste mundo com o vosso servo o Papa e o nosso Bispo, com os bispos do mundo inteiro,
        os presbíteros e diáconos, os outros ministros e o povo por vós redimido. Atendei propício às preces desta
        família, que reunistes em vossa presença. Reconduzi a vós, Pai de misericórdia, todos os vossos filhos
        e filhas dispersos pelo mundo inteiro.</div>
      <div class="response"><strong>T. Lembrai-vos, ó Pai, da vossa Igreja!</strong></div>
      <div class="dialogue"><span class="label-p">P.</span> Acolhei com bondade no vosso reino os nossos irmãos e
        irmãs que partiram desta vida e todos os que morreram na vossa amizade. Unidos a eles, esperamos também
        nós saciar-nos eternamente da vossa glória, por Cristo, Senhor nosso. Por ele dais ao mundo todo bem e
        toda graça.</div>
      ${doxologia}`;
  }

  // ===== INTRODUCTIONS BY LITURGICAL SEASON =====
  function getIntroduction(data) {
    if (!data) return '';
    const lit = (data.liturgia || '').toLowerCase();
    if (lit.includes('quaresma')) {
      return 'Irmãos e irmãs, vivemos este Tempo da Quaresma na intensa preparação para a celebração anual da Páscoa do Senhor, e deixemos que Deus, em seu infinito amor, reacenda em nós a chama batismal. Com Jesus, entramos ao deserto da existência humana para, também com Ele, vencermos as ciladas do inimigo e o tormento da maldade. Impulsionados pela Campanha da Fraternidade 2026, meditemos e anunciemos o querer de Deus: que todos tenham uma moradia e uma vida dignas. Celebremos com fé este Dia do Senhor.';
    }
    if (lit.includes('advento')) {
      return 'Irmãos e irmãs, o Tempo do Advento nos convida a preparar o caminho do Senhor. Acolhamos com alegria a vinda do Salvador e nos preparemos para celebrar o Natal com corações renovados pela fé e pela esperança.';
    }
    if (lit.includes('páscoa') || lit.includes('pascoa')) {
      return 'Irmãos e irmãs, celebramos a vitória de Cristo sobre a morte. O Senhor ressuscitou! Alegrai-vos, pois Ele vive e caminha conosco, renovando a nossa esperança e fortalecendo a nossa fé.';
    }
    return 'Irmãos e irmãs, reunidos como comunidade de fé, celebremos com alegria os sagrados mistérios, acolhendo a Palavra de Deus que ilumina o nosso caminho e nos fortalece na esperança.';
  }

  // ===== ATO PENITENCIAL =====
  function getAtoPenitencial(data) {
    if (!data) return '';
    // Formula III (invocações) - matches the user's book
    return `
      <div class="dialogue"><span class="label-p">P.</span> O Senhor disse: "Quem dentre vós estiver sem pecado, atire a primeira pedra". Reconheçamo-nos todos pecadores e perdoemo-nos mutuamente do fundo do coração. <em>(silêncio)</em></div>
      <div class="dialogue"><span class="label-p">PR.</span> Senhor, que na cruz perdoastes o ladrão arrependido, tende piedade de nós.</div>
      <div class="response"><strong>AS: Tende piedade de nós</strong></div>
      <div class="dialogue"><span class="label-p">PR.</span> Cristo, que nos mandastes perdoar-nos mutuamente antes de nos aproximar do vosso altar, tende piedade de nós.</div>
      <div class="response"><strong>AS: Tende piedade de nós</strong></div>
      <div class="dialogue"><span class="label-p">PR.</span> Senhor, que confiastes à vossa Igreja o ministério da reconciliação, tende piedade de nós.</div>
      <div class="response"><strong>AS: Tende piedade de nós</strong></div>
      <div class="separator"></div>
      <div class="dialogue"><span class="label-p">P.</span> Deus todo-poderoso tenha compaixão de nós, perdoe os nossos pecados e nos conduza à vida eterna.</div>
      <div class="response"><strong>T. Amém.</strong></div>
    `;
  }

  // ===== API =====
  async function fetchLiturgy(date) {
    const url = `https://liturgia.up.railway.app/${fmtAPI(date)}`;
    const key = `liturgia_${fmtISO(date)}`;
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(10000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      try { localStorage.setItem(key, JSON.stringify(data)); } catch (e) { }
      try { localStorage.setItem('liturgia_last', JSON.stringify(data)); } catch (e) { }
      return { data, offline: false };
    } catch (e) {
      console.warn('API error:', e);
      const c = localStorage.getItem(key) || localStorage.getItem('liturgia_last');
      if (c) return { data: JSON.parse(c), offline: true };
      return { data: null, offline: true };
    }
  }

  // ===== RENDER =====
  function esc(t) { return t ? t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') : ''; }

  function fmtReading(t) {
    if (!t) return '';
    let s = t.replace(/(\d+)([A-ZÀ-ÚÉÊÍÓa-zà-ú])/g, '<sup>$1</sup>$2');
    return s.replace(/\n/g, '<br>');
  }

  function renderSalmo(salmo) {
    const c = $('#salmoVerses'); c.innerHTML = '';
    const refrao = salmo.refrao || '';
    const verses = (salmo.texto || '').split(/\n–\s*/).filter(v => v.trim());
    verses.forEach((v, i) => {
      v = v.replace(/^–\s*/, '').trim();
      if (!v) return;
      const d = document.createElement('div'); d.className = 'psalm-verse';
      d.innerHTML = esc(v); c.appendChild(d);
      if (refrao && i < verses.length - 1) {
        const r = document.createElement('div'); r.className = 'refrain';
        r.textContent = refrao; c.appendChild(r);
      }
    });
    if (refrao) {
      const r = document.createElement('div'); r.className = 'refrain';
      r.textContent = refrao; c.appendChild(r);
    }
  }

  function renderMemorial() {
    const day = Math.floor((currentDate - new Date(currentDate.getFullYear(), 0, 0)) / 86400000);
    const idx = day % 3;
    const c = $('#memorialOptions'); c.innerHTML = '';
    const d = document.createElement('div'); d.className = 'response';
    d.innerHTML = `<strong>T.</strong> ${MEMORIAL[idx]}`; c.appendChild(d);
    const alt = document.createElement('div');
    alt.style.cssText = 'margin-top:0.6rem;font-size:0.8rem;color:var(--text-muted);';
    alt.innerHTML = '<em>Outras fórmulas:</em>';
    MEMORIAL.forEach((o, i) => {
      if (i !== idx) {
        const p = document.createElement('div');
        p.style.cssText = 'padding:0.2rem 0;font-size:0.82rem;line-height:1.5;';
        p.textContent = `• ${o}`; alt.appendChild(p);
      }
    });
    c.appendChild(alt);
  }

  async function render(data, offline) {
    liturgyData = data;
    console.log('[render] ✓ Iniciado render()');

    // Date
    $('#datePicker').value = fmtISO(currentDate);

    // Offline
    const oa = $('#offlineArea'); oa.innerHTML = '';
    if (offline) {
      oa.innerHTML = '<div class="offline-notice">⚠ Modo offline — exibindo dados em cache</div>';
    }

    if (!data) {
      $('#heroFeast').textContent = 'Liturgia do Dia';
      $('#headerSub').textContent = 'SantaLitu | Sem conexão';
      return;
    }

    // Color
    const ck = (data.cor || 'verde').toLowerCase();
    const ci = LIT_COLORS[ck] || LIT_COLORS['verde'];
    document.documentElement.style.setProperty('--purple', ci.hex);
    $('#litDot').style.background = ci.hex;
    $('#colorBadge').style.borderColor = ci.hex;
    $('#colorBadge').style.color = ci.hex;
    $('#colorLabel').textContent = ci.label;
    // Update header color
    const headerEl = $('#appHeader');
    headerEl.style.background = ci.hex;

    // Hero
    $('#heroFeast').textContent = data.liturgia || 'Liturgia do Dia';

    // Header sub
    const seasonText = (data.liturgia || '').includes('Quaresma') ? 'Quaresma' :
      (data.liturgia || '').includes('Advento') ? 'Advento' :
        (data.liturgia || '').includes('Páscoa') ? 'Páscoa' : 'Tempo Comum';
    $('#headerSub').textContent = `Liturgia Diária | ${seasonText}`;

    // Credo badge
    const showCredo = isDomingo(data);
    $('#credoBadge').style.display = showCredo ? 'inline-flex' : 'none';
    if (showCredo) {
      $('#credoBadge').style.borderColor = ci.hex;
      $('#credoBadge').style.color = ci.hex;
    }

    // Introduction
    $('#introText').innerHTML = getIntroduction(data);

    // Antifona entrada
    $('#antifonaEntrada').innerHTML = data.antifonas ? esc(data.antifonas.entrada) : '';

    // Ato penitencial
    $('#atoPenitencialContent').innerHTML = getAtoPenitencial(data);

    // Gloria
    const sg = shouldShowGloria(data);
    if (sg) {
      $('#sec-gloria').style.display = 'block';
      $('#gloriaNote').style.display = 'none';
    } else {
      $('#sec-gloria').style.display = 'none';
      $('#gloriaNote').style.display = 'block';
      const noteText = isQuaresma(data)
        ? 'Nota Litúrgica: Durante a Quaresma, o Hino de Louvor (Glória) não é cantado.'
        : 'Nota Litúrgica: O Glória não é recitado nas férias do Tempo Comum e do Advento.';
      $('#gloriaRubric').innerHTML = `<strong>Nota Litúrgica:</strong> ${noteText.replace('Nota Litúrgica: ', '')}`;
    }

    // Coleta
    $('#oracaoColeta').innerHTML = esc(data.dia || '');

    // 1ª Leitura
    if (data.primeiraLeitura) {
      $('#leitura1Ref').textContent = data.primeiraLeitura.referencia || '';
      $('#leitura1RefBtn').textContent = data.primeiraLeitura.referencia || '';
      $('#leitura1Titulo').textContent = data.primeiraLeitura.titulo || '';
      $('#leitura1Texto').innerHTML = fmtReading(data.primeiraLeitura.texto || '');
    }

    // Salmo
    if (data.salmo) {
      $('#salmoRef').textContent = data.salmo.referencia || '';
      $('#salmoRefrao').textContent = data.salmo.refrao || '';
      renderSalmo(data.salmo);
    }

    // 2ª Leitura
    if (data.segundaLeitura && data.segundaLeitura.referencia) {
      $('#sec-leitura2').style.display = 'block';
      $('#leitura2Ref').textContent = data.segundaLeitura.referencia || '';
      $('#leitura2RefBtn').textContent = data.segundaLeitura.referencia || '';
      $('#leitura2Titulo').textContent = data.segundaLeitura.titulo || '';
      $('#leitura2Texto').innerHTML = fmtReading(data.segundaLeitura.texto || '');
    } else {
      $('#sec-leitura2').style.display = 'none';
    }

    // Aclamação
    if (isQuaresma(data)) {
      $('#aclamacaoTexto').innerHTML = '<strong>Louvor e glória a vós, Senhor Jesus Cristo!</strong>';
    } else {
      $('#aclamacaoTexto').innerHTML = '<strong>Aleluia, Aleluia, Aleluia!</strong>';
    }

    // Evangelho
    if (data.evangelho) {
      $('#evangelhoRef').textContent = data.evangelho.referencia || '';
      $('#evangelhoRefBtn').textContent = data.evangelho.referencia || '';
      $('#evangelista').textContent = getEvangelista(data.evangelho.referencia);
      $('#evangelhoTexto').innerHTML = fmtReading(data.evangelho.texto || '');
    }

    // Credo
    const credoSection = $('#sec-credo');
    if (isDomingo(data)) {
      credoSection.style.display = 'block';
      $('#credoRubric').textContent = '';
    } else {
      credoSection.style.display = 'none';
    }

    // Preces (async - tenta JSON do crawler primeiro)
    // ⚠ IMPORTANTE: aguardar loadPreces() para garantir que OE seja corretamente carregada do JSON
    console.log('[render] ➤ render: chamando loadPreces() com AWAIT');
    await loadPreces(data);
    console.log('[render] ✓ loadPreces() completou');

    // Oferendas
    $('#oracaoOferendas').innerHTML = esc(data.oferendas || '');

    // Memorial
    renderMemorial();

    // Comunhão
    $('#antifonaComunhao').innerHTML = data.antifonas ? esc(data.antifonas.comunhao) : '';
    $('#oracaoPosComunhao').innerHTML = esc(data.comunhao || '');

    // Apply mode filtering
    applyMode();
  }

  // ===== LOAD =====
  async function loadDay(date) {
    currentDate = new Date(date);
    // Show loading state
    const content = $('#massContent');
    content.style.opacity = '0.4';
    content.style.pointerEvents = 'none';

    const { data, offline } = await fetchLiturgy(currentDate);
    await render(data, offline);

    content.style.opacity = '1';
    content.style.pointerEvents = '';
  }

  // ===== COLLAPSIBLE SECTIONS =====
  function initToggles() {
    document.addEventListener('click', e => {
      const btn = e.target.closest('.section-toggle');
      if (!btn) return;
      const bodyId = btn.dataset.section;
      const body = document.getElementById(bodyId);
      if (!body) return;
      const icon = btn.querySelector('.toggle-icon');
      body.classList.toggle('collapsed');
      icon.textContent = body.classList.contains('collapsed') ? '＋' : '−';
    });
  }

  // ===== EXPAND/COLLAPSE ALL =====
  function expandAll() {
    $$('.section-body').forEach(b => { b.classList.remove('collapsed'); });
    $$('.toggle-icon').forEach(i => { i.textContent = '−'; });
  }
  function collapseAll() {
    $$('.section-body').forEach(b => { b.classList.add('collapsed'); });
    $$('.toggle-icon').forEach(i => { i.textContent = '＋'; });
  }

  // ===== DATE NAV =====
  function initDateNav() {
    $('#prevDay').addEventListener('click', () => {
      const d = new Date(currentDate); d.setDate(d.getDate() - 1); loadDay(d);
    });
    $('#nextDay').addEventListener('click', () => {
      const d = new Date(currentDate); d.setDate(d.getDate() + 1); loadDay(d);
    });
    $('#datePicker').addEventListener('change', e => {
      const v = e.target.value;
      if (v) {
        const parts = v.split('-');
        loadDay(new Date(parts[0], parts[1] - 1, parts[2]));
      }
    });
  }

  // ===== FONT SIZE =====
  function initFontControls() {
    let size = parseInt(localStorage.getItem('santalitu_fs') || '16');
    document.documentElement.style.setProperty('--font-size', size);
    $('#fontLabel').textContent = size + 'px';

    $('#fontDown').addEventListener('click', () => {
      size = Math.max(12, size - 2);
      document.documentElement.style.setProperty('--font-size', size);
      $('#fontLabel').textContent = size + 'px';
      localStorage.setItem('santalitu_fs', size);
    });
    $('#fontUp').addEventListener('click', () => {
      size = Math.min(24, size + 2);
      document.documentElement.style.setProperty('--font-size', size);
      $('#fontLabel').textContent = size + 'px';
      localStorage.setItem('santalitu_fs', size);
    });
  }

  // ===== BOTTOM NAV MODES =====
  const MISSA_ALL = ['sec-intro', 'sec-antifona', 'sec-saudacao', 'sec-penitencial', 'gloriaNote', 'sec-gloria', 'sec-coleta', 'sec-leitura1', 'sec-salmo', 'sec-leitura2', 'sec-aclamacao', 'sec-evangelho', 'sec-homilia', 'sec-credo', 'sec-preces', 'sec-ofertorio', 'sec-oferendas', 'sec-prefacio', 'sec-eucaristica', 'sec-painosso', 'sec-paz', 'sec-cordeiro', 'sec-comungar', 'sec-antcomunhao', 'sec-poscomunhao', 'sec-final'];
  const LEITURAS_ONLY = ['sec-leitura1', 'sec-salmo', 'sec-leitura2', 'sec-aclamacao', 'sec-evangelho'];
  const DEVOCAO_SECTIONS = ['sec-intro', 'sec-painosso', 'sec-credo', 'sec-preces'];

  function applyMode() {
    const visible = currentMode === 'missa' ? MISSA_ALL : currentMode === 'leituras' ? LEITURAS_ONLY : DEVOCAO_SECTIONS;
    MISSA_ALL.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      // Don't override sections hidden by liturgical rules
      if (id === 'sec-leitura2' && liturgyData && !(liturgyData.segundaLeitura && liturgyData.segundaLeitura.referencia)) return;
      if (id === 'sec-gloria' && !shouldShowGloria(liturgyData)) return;
      if (id === 'gloriaNote' && shouldShowGloria(liturgyData)) return;
      if (id === 'sec-credo' && !isDomingo(liturgyData)) return;
      el.style.display = visible.includes(id) ? '' : 'none';
    });

    // Show/hide part dividers
    $$('.part-divider').forEach(d => {
      d.style.display = currentMode === 'missa' ? '' : 'none';
    });
  }

  function initBottomNav() {
    $$('.bnav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        $$('.bnav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
        applyMode();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });
  }

  // ===== SERVICE WORKER =====
  function registerSW() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('service-worker.js').catch(() => { });
    }
  }

  // ===== INIT =====
  async function init() {
    initToggles();
    initDateNav();
    initFontControls();
    initBottomNav();
    registerSW();

    // Expand all sections by default for continuous reading
    expandAll();

    await loadDay(new Date());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
