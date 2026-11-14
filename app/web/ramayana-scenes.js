/* Fifty-five Ramayana beats, in order. Text defaults live here; admins can override them. */
(function (root) {
  const GAGS = [
    "Yeh gada ab meri hai. Jetpack, chalo!",
    "Diya chura ke Mars nahi, seedha mischief.",
    "Narad ji ki line bhi main chura lunga.",
    "Setu ka patthar? Pocket mein daal liya.",
    "Arrow nahi chahiye, gada chahiye.",
    "Ring utha li. Launch button samajh ke.",
    "Main har scene ka bad guy hoon. Sorry nahi.",
    "Samaan lo, trouble do, ud jao.",
    "Pushpak se tez, aur zyada badmaash.",
    "Ram Rajya mein bhi ek chori extra.",
    "Bonk se pehle ek aur cheez.",
    "Heroes ki line mein mera naam nahi. Main villain hoon.",
    "Gada kandhe pe, cape peeche, phir se.",
  ];

  const PLANS = [
    "Beta, plan yeh hai: churao, phir ud jao.",
    "Pehle main ungli hilaunga, phir tum gada lo.",
    "Diya bujhana. Main dekh raha hoon.",
    "Setu pe mat tikna, mischief pe tikna.",
    "Narad ki line ke beech hum dono ghusenge.",
    "Ring unki hai, plan mera hai.",
    "Main sochta hoon, tum udte ho.",
    "Dono bhaagenge, plan phir bhi mera hai.",
    "Pushpak se pehle ek chhoti si chori.",
    "Ram Rajya mein bhi ek senior partner chahiye.",
    "Bonk aayega. Plan phir bhi mera hai.",
    "Heroes ki line mein hum dono extra hain.",
    "Stick se point, jetpack se exit.",
  ];

  const BLESSINGS = [
    "Main Valmiki. Yeh katha maine likhi. Sab ruko, pranam.",
    "Narad, aage badho. Mera aashirvad saath hai.",
    "Hath jodo. Jo chori chal rahi thi, woh yahin rukti hai.",
    "Palm-patra pe yeh pankti hai: prem se jhuko.",
    "Betaon, dhanush neeche. Sir jhukaao.",
    "Aashirvad. Ab katha phir chale.",
    "Ant mein bhi main hoon. Ram Rajya par shanti.",
  ];

  function beat(id, title, backdrop, caption, cast, extras) {
    return { id, title, backdrop, caption, cast, extras: extras || [] };
  }

  const forest = ["team-1", "team-2", "team-3"];
  const crowd = ["team-1", "team-2", "team-3", "team-4", "team-5", "team-6", "team-7", "team-8"];

  const BEATS = [
    beat("s01", "Ayodhya", "palace", "Narayan Narayan. Ayodhya ka darbar chamak raha hai.", "rama~left~walk~Yeh hamara ghar hai.|sita~right~walk~Phoolon jaisi subah.|lakshmana~left~bow~Main peeche hoon."),
    beat("s02", "Dasharatha wish", "palace", "Narayan Narayan. Raja Dasharatha bete ka sapna dekhte hain.", "rama~left~bow~Pitaji, aashirwad.|narad~right~walk~Katha yahin se lambi hai."),
    beat("s03", "Vishwamitra arrives", "palace", "Narayan Narayan. Vishwamitra rishi darbar mein aaye.", "rama~left~bow~Hum taiyar hain.|lakshmana~right~walk~Guru ji, chaliye."),
    beat("s04", "Tadaka", "fight", "Narayan Narayan. Tadaka ka jangal shant hota hai.", "rama~left~shoot~Ek dhanush, kaam khatam.|lakshmana~right~shoot~Main cover karta hoon."),
    beat("s05", "Forest lessons", "forest", "Narayan Narayan. Vishwamitra astras sikhate hain.", "rama~left~bow~Dhanush seedha.|lakshmana~right~bow~Nazar nishane pe."),
    beat("s06", "Road to Mithila", "forest", "Narayan Narayan. Mithila ki sadak khul rahi hai.", "rama~left~walk~Aage kya hai?|lakshmana~right~walk~Ek bada dhanush, suna hai.|sita~right~walk~Janakpur intezar kar raha hai."),
    beat("s07", "Breaking the Shiva bow", "palace", "Narayan Narayan. Shiva ka dhanush Rama tod dete hain.", "rama~left~shoot~Yeh dhanush toot gaya!|sita~right~cheer~Yeh woh hain."),
    beat("s08", "Sita swayamvar", "palace", "Narayan Narayan. Sita ke swayamvar mein vara mil gaya.", "sita~left~walk~Mera vara.|rama~right~bow~Main saath hoon.|narad~top~walk~Kya scene hai!"),
    beat("s09", "The wedding", "palace", "Narayan Narayan. Vivah ki agni jal rahi hai.", "rama~left~walk~Saptapadi.|sita~right~walk~Saath chalte hain.|lakshmana~left~cheer~Bhaiya ki jai."),
    beat("s10", "Home to Ayodhya", "palace", "Narayan Narayan. Baraat Ayodhya laut ti hai.", "rama~left~walk~Ghar aa gaye.|sita~right~walk~Naye phool.|lakshmana~right~walk~Darwaze kholo."),
    beat("s11", "Kaikeyi boons", "palace", "Narayan Narayan. Kaikeyi do boon maangti hain.", "rama~left~bow~Pitaji ka vachan.|narad~right~walk~Manthara ki baat mehngi padi."),
    beat("s12", "Exile", "forest", "Narayan Narayan. Exile ka rasta jungle ki taraf hai.", "rama~left~walk~Chaudah varsh.|sita~right~walk~Main bhi chalogi.|lakshmana~left~walk~Akele nahi."),
    beat("s13", "The palace gate", "palace", "Narayan Narayan. Rajmahal ka dwar peeche chhoot ta hai.", "rama~right~walk~Mud kar nahi dekhunga.|lakshmana~left~bow~Dhanush saath hai."),
    beat("s14", "Forest path", "forest", "Narayan Narayan. Pedon ke beech teen chalte hain.", "rama~left~walk~Nadi aage hai.|sita~right~walk~Chhaya achhi hai.|lakshmana~right~walk~Main peeche dekhta hoon.", forest),
    beat("s15", "Crossing the river", "river", "Narayan Narayan. Nadi ke us paar vanvas hai.", "rama~left~walk~Nav chhoti hai.|lakshmana~right~walk~Main dor pakadta hoon.|sita~right~walk~Paani thanda hai."),
    beat("s16", "Chitrakoot", "forest", "Narayan Narayan. Chitrakoot ki pahadi shant hai.", "rama~left~walk~Yahin rukte hain.|sita~right~walk~Phool todungi.", forest),
    beat("s17", "Bharata hears", "palace", "Narayan Narayan. Bharata ko khabar milti hai.", "lakshmana~left~walk~Bharata aa rahe hain.|rama~right~bow~Bhai ko gussa nahi, prem hai."),
    beat("s18", "Bharata meets Rama", "forest", "Narayan Narayan. Bharata Rama ke charan pakadte hain.", "rama~left~walk~Rajya tum sambhalo.|lakshmana~right~bow~Bhaiya, woh ro rahe hain."),
    beat("s19", "The padukas", "forest", "Narayan Narayan. Padukas Bharata ke haath mein hain.", "rama~left~walk~Yeh paduka raj sinhasan pe rakho.|lakshmana~right~bow~Vachan poora."),
    beat("s20", "Nandigram", "palace", "Narayan Narayan. Bharata Nandigram se rajya chalate hain.", "narad~left~walk~Paduka hi raja hain.|rama~right~walk~Vanvas jaari hai."),
    beat("s21", "Years in the forest", "forest", "Narayan Narayan. Vanvas ke saal dheere jaate hain.", "rama~left~walk~Ek aur season.|sita~right~walk~Kahani aage badhegi.|lakshmana~right~bow~Pehra mera.", forest),
    beat("s22", "Panchavati", "forest", "Narayan Narayan. Panchavati mein kutiya banti hai.", "rama~left~walk~Yeh Panchavati hai.|sita~right~walk~Chulha yahin.|lakshmana~right~walk~Rekha baad mein kaam aayegi.", forest),
    beat("s23", "Surpanakha", "fight", "Narayan Narayan. Surpanakha ka mazak bhaari padta hai.", "lakshmana~left~shoot~Hadd ke bahar.|rama~right~bow~Shant raho."),
    beat("s24", "The golden deer", "forest", "Narayan Narayan. Golden deer Sita ko bhaata hai.", "sita~left~walk~Woh hirna sona hai!|rama~right~shoot~Main laata hoon.|lakshmana~left~bow~Yeh jaal lagta hai."),
    beat("s25", "The false cry", "forest", "Narayan Narayan. Jhooti awaaz jungle mein gunjti hai.", "lakshmana~left~walk~Bhaiya ki awaaz?|sita~right~walk~Jao, dekho!"),
    beat("s26", "Lakshman Rekha", "forest", "Narayan Narayan. Lakshman Rekha kutiya ke aage hai.", "lakshmana~left~walk~Rekha ke us paar mat aana.|sita~right~walk~Main yahin hoon."),
    beat("s27", "Sita abduction", "fight", "Narayan Narayan. Sita ka haran ho jata hai.", "sita~left~walk~Rama!|ravana~right~fly~Pushpak ka chhota bhai, meri sawari."),
    beat("s28", "Jatayu", "fight", "Narayan Narayan. Jatayu panchhi Ravana se ladta hai.", "rama~left~run~Jatayu, kaun le gaya?|lakshmana~right~run~Pankh toot gaye, himmat nahi."),
    beat("s29", "The search", "forest", "Narayan Narayan. Rama aur Lakshmana khojte hain.", "rama~left~walk~Sita kahan?|lakshmana~right~walk~Dakshin disha.", forest),
    beat("s30", "Shabari", "forest", "Narayan Narayan. Shabari ke ber meethhe hain.", "rama~left~walk~Yeh ber prasada hai.|sita~right~walk~Prem sabse bada phal."),
    beat("s31", "Meeting Hanuman", "forest", "Narayan Narayan. Hanuman mile, poonchh lambi hai.", "hanuman~left~leap~Kiske vanar ho aap?|rama~right~walk~Mitra mil gaya."),
    beat("s32", "Meeting Sugriva", "forest", "Narayan Narayan. Sugriva Rama se dosti karte hain.", "sugriva~left~walk~Vali se dar hai.|rama~right~bow~Dosti nibhaunga.|hanuman~right~walk~Main gaawah hoon."),
    beat("s33", "Vali", "fight", "Narayan Narayan. Vali ka yuddh khatam hota hai.", "rama~left~shoot~Ek baan.|sugriva~right~walk~Rajya ab nyay se.|hanuman~left~cheer~Sugriva ki jai."),
    beat("s34", "The search party", "forest", "Narayan Narayan. Search party char disha nikal ti hai.", "hanuman~left~run~Dakshin mera.|sugriva~right~walk~Sena taiyar.|jambavan~left~walk~Main bhi chalta hoon.", forest),
    beat("s35", "The southern shore", "river", "Narayan Narayan. Samundar kinare vanar sena rukti hai.", "hanuman~left~walk~Paani beant.|jambavan~right~walk~Yaad karo apni taakat.", crowd),
    beat("s36", "Hanuman leap", "leap", "Narayan Narayan. Hanuman ka leap samundar paar karta hai.", "hanuman~left~leap~Jai Shri Rama!|jambavan~right~cheer~Ud jao!"),
    beat("s37", "Ashok Vatika", "garden", "Narayan Narayan. Ashok Vatika mein Sita akeli hain.", "sita~left~walk~Ashok ke ped.|hanuman~right~sit~Chupke se aaya hoon."),
    beat("s38", "The ring", "garden", "Narayan Narayan. Rama ki ring Sita ke haath mein hai.", "hanuman~left~walk~Yeh ring unki hai.|sita~right~walk~Ab bharosa hai."),
    beat("s39", "Sita message", "garden", "Narayan Narayan. Sita ka sandesh Lanka se nikalta hai.", "sita~left~walk~Kaho, main intezar kar rahi hoon.|hanuman~right~leap~Sandesh pahuncha dunga."),
    beat("s40", "Lanka tail fire", "lanka", "Narayan Narayan. Lanka ki aag Hanuman ki poonchh se hai.", "hanuman~left~run~Poonchh mein aag, iraada seedha.|ravana~right~walk~Yeh kaun vanar hai!"),
    beat("s41", "News for Rama", "forest", "Narayan Narayan. Hanuman wapas Sita ki khabar laate hain.", "hanuman~left~leap~Sita mili!|rama~right~walk~Ab sena chalegi.|lakshmana~left~bow~Dhanush taiyar."),
    beat("s42", "The army marches", "forest", "Narayan Narayan. Vanar sena samundar ki taraf badhti hai.", "sugriva~left~run~Chalo!|hanuman~right~run~Aage raasta.|jambavan~left~walk~Dheere nahi.", crowd),
    beat("s43", "Ram Setu", "bridge", "Narayan Narayan. Ram Setu pattharon se banta hai.", "rama~left~walk~Naam likho.|hanuman~right~walk~Patthar lao.", crowd),
    beat("s44", "Stones float on Ram", "bridge", "Narayan Narayan. Ram naam se patthar tair rahe hain.", "hanuman~left~cheer~Ram, aur patthar utra!|rama~right~walk~Setu jud raha hai.|vibhishana~right~walk~Main door se dekh raha tha."),
    beat("s45", "Vibhishana joins", "bridge", "Narayan Narayan. Vibhishana Rama ki sharan aate hain.", "vibhishana~left~bow~Main saath hoon, hath jode.|rama~right~walk~Sharan ko dwar hai."),
    beat("s46", "Angad foot", "lanka", "Narayan Narayan. Angad ka pair sabha mein gadh jata hai.", "sugriva~left~walk~Angad ka pair mat hila.|ravana~right~walk~Yeh sabha hil gayi."),
    beat("s47", "Kumbhakarna wakes", "fight", "Narayan Narayan. Kumbhakarna ki neend toot ti hai.", "kumbhakarna~left~walk~Aur paanch minute...|ravana~right~walk~Utho, yuddh hai!"),
    beat("s48", "Kumbhakarna fights", "fight", "Narayan Narayan. Kumbhakarna gada le kar aate hain.", "kumbhakarna~left~fight~Gada bhaari hai.|rama~right~shoot~Neend ab poori.", crowd),
    beat("s49", "Indrajit", "fight", "Narayan Narayan. Indrajit maya se teer chalata hai.", "lakshmana~left~shoot~Dhuan hai, dhanush nahi.|rama~right~bow~Lakshmana, sambhal."),
    beat("s50", "Lakshmana falls", "fight", "Narayan Narayan. Lakshmana maidan mein girte hain.", "lakshmana~left~walk~Bhaiya...|rama~right~walk~Main yahin hoon.|hanuman~left~run~Dawai chahiye."),
    beat("s51", "Sanjeevani", "mountain", "Narayan Narayan. Sanjeevani ke liye Hanuman parvat uthate hain.", "hanuman~left~leap~Pahad saath le chala.|lakshmana~right~walk~Saans wapas.|jambavan~left~cheer~Yahi jadi booti hai."),
    beat("s52", "Final battle", "fight", "Narayan Narayan. Antim yuddh Lanka ke dwar pe hai.", "rama~left~shoot~Aaj faisla.|ravana~right~fight~Das sar, ek galti.|lakshmana~left~shoot~Main saath hoon.", crowd),
    beat("s53", "Arrows at Ravana", "fight", "Narayan Narayan. Baan Ravana ke siron ki taraf jaate hain.", "rama~left~shoot~Har sir pe ek katha.|hanuman~right~fight~Gada bhi taiyar.|ravana~right~fight~Cartoon dhakka, dar nahi."),
    beat("s54", "Victory", "lanka", "Narayan Narayan. Victory ke nagaade bajte hain.", "rama~left~cheer~Sita wapas.|sita~right~walk~Ghar chalein.|vibhishana~left~bow~Lanka shant.", crowd),
    beat("s55", "Pushpak Diwali Ram Rajya", "diwali", "Narayan Narayan. Pushpak Vimana, Diwali, aur Ram Rajya.", "rama~left~fly~Ayodhya ke diye.|sita~right~walk~Ghar ki roshni.|hanuman~left~cheer~Jai Shri Rama!|narad~right~walk~Katha poori, phir se shuru.", crowd),
  ];

  function playFor(backdrop) {
    if (backdrop === "fight" || backdrop === "lanka") return "slash";
    if (backdrop === "bridge") return "stack";
    if (backdrop === "garden") return "sit";
    if (backdrop === "leap" || backdrop === "mountain") return "juggle";
    return "wander";
  }

  function actorsFrom(cast) {
    return cast.split("|").filter(Boolean).map(function (part) {
      const bits = part.split("~");
      return { id: bits[0], entry: bits[1] || "left", action: bits[2] || "walk", line: bits[3] || "" };
    });
  }

  function list() {
    return BEATS.map(function (beat, index) {
      const actors = actorsFrom(beat.cast);
      const lines = { narad: beat.caption };
      actors.forEach(function (actor) { lines[actor.id] = actor.line; });
      const gag = index % 4 === 3;
      if (gag) {
        const gagIndex = Math.floor(index / 4);
        lines["rocket-boss"] = GAGS[gagIndex % GAGS.length];
        lines["old-man-boss"] = PLANS[gagIndex % PLANS.length];
        lines.chase = "Pakdo Rocket Boss aur Old Man Boss ko!";
      }
      const blessing = index === 0 || index === BEATS.length - 1 || index % 9 === 0;
      if (blessing) lines.valmiki = BLESSINGS[Math.floor(index / 9) % BLESSINGS.length];
      return {
        id: beat.id,
        title: beat.title,
        backdrop: beat.backdrop,
        caption: beat.caption,
        actors: actors,
        extras: beat.extras,
        lines: lines,
        gag: gag,
        blessing: blessing,
        play: playFor(beat.backdrop),
        duration: beat.id === "s55" ? 12000 : 6000 + (index % 7) * 800,
      };
    });
  }

  function rows() {
    return list().flatMap(function (scene) {
      const out = [{ scene_id: scene.id, actor: "narad", label: scene.title + " · Narad", text: scene.caption }];
      scene.actors.forEach(function (actor) {
        out.push({ scene_id: scene.id, actor: actor.id, label: scene.title + " · " + actor.id, text: actor.line });
      });
      if (scene.gag) {
        out.push({ scene_id: scene.id, actor: "rocket-boss", label: scene.title + " · Rocket Boss", text: scene.lines["rocket-boss"] });
        out.push({ scene_id: scene.id, actor: "old-man-boss", label: scene.title + " · Old Man Boss", text: scene.lines["old-man-boss"] });
        out.push({ scene_id: scene.id, actor: "chase", label: scene.title + " · chase", text: scene.lines.chase });
      }
      if (scene.blessing) {
        out.push({ scene_id: scene.id, actor: "valmiki", label: scene.title + " · Maharishi Valmiki", text: scene.lines.valmiki });
      }
      return out;
    });
  }

  const api = { list: list, rows: rows };
  root.RamayanaScenes = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
