import collections
import hashlib
import json
import statistics

from research_cli import arguments, require_files, run


def main():
    args = arguments("validate_polyvore_original")
    root, CATEGORIES = args.source, args.categories
    require_files(
        CATEGORIES,
        *(
            root / name
            for name in (
                "train_no_dup.json",
                "valid_no_dup.json",
                "test_no_dup.json",
                "fill_in_blank_test.json",
                "fashion_compatibility_prediction.txt",
            )
        ),
    )

    splits = {}
    all_sets = {}
    all_items = {}
    refs_by_split = {}
    for split, fn in [
        ("train", "train_no_dup.json"),
        ("valid", "valid_no_dup.json"),
        ("test", "test_no_dup.json"),
    ]:
        data = json.load(open(root / fn, encoding="utf-8"))
        splits[split] = data
        ids = []
        lens = []
        missing_out = collections.Counter()
        missing_item = collections.Counter()
        cats = collections.Counter()
        item_ids = []
        for o in data:
            sid = str(o["set_id"])
            ids.append(sid)
            lens.append(len(o["items"]))
            all_sets[sid] = (split, o)
            for k in [
                "name",
                "views",
                "items",
                "image",
                "likes",
                "date",
                "set_url",
                "set_id",
                "desc",
            ]:
                if k not in o or o[k] is None:
                    missing_out[k] += 1
            for it in o["items"]:
                iid = f"{sid}_{it['index']}"
                item_ids.append(iid)
                all_items[iid] = (split, it)
                cats[str(it["categoryid"])] += 1
                for k in ["index", "name", "price", "likes", "image", "categoryid"]:
                    if k not in it or it[k] is None:
                        missing_item[k] += 1
        refs_by_split[split] = set(item_ids)
        print(
            split,
            "outfits",
            len(data),
            "unique_set_ids",
            len(set(ids)),
            "items",
            len(item_ids),
            "unique_item_refs",
            len(set(item_ids)),
            "len_min_med_mean_max",
            min(lens),
            statistics.median(lens),
            round(statistics.mean(lens), 3),
            max(lens),
            "missing_out",
            dict(missing_out),
            "missing_item",
            dict(missing_item),
            "categories",
            len(cats),
        )
    print(
        "set overlap",
        {
            a + "-" + b: len(
                set(str(o["set_id"]) for o in splits[a]) & set(str(o["set_id"]) for o in splits[b])
            )
            for a, b in [("train", "valid"), ("train", "test"), ("valid", "test")]
        },
    )
    print(
        "outfit-position reference overlap (not product identity)",
        {
            a + "-" + b: len(refs_by_split[a] & refs_by_split[b])
            for a, b in [("train", "valid"), ("train", "test"), ("valid", "test")]
        },
    )
    # category map
    catmap = {}
    for line in CATEGORIES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            k, v = line.split(" ", 1)
            catmap[k] = v
    used = {str(it["categoryid"]) for _, it in all_items.values()}
    print(
        "category_map_count",
        len(catmap),
        "used_count",
        len(used),
        "used_unmapped",
        sorted(used - set(catmap), key=int),
        "mapping_unused",
        len(set(catmap) - used),
    )
    # FITB
    fitb = json.load(open(root / "fill_in_blank_test.json", encoding="utf-8"))
    anslens = collections.Counter(len(q["answers"]) for q in fitb)
    qlens = collections.Counter(len(q["question"]) for q in fitb)
    all_refs = []
    correct_in_test = 0
    missing = []
    wrongpos = []
    for q in fitb:
        refs = q["question"] + q["answers"]
        all_refs += refs
        missing += [x for x in refs if x not in all_items]
        correct = q["answers"][0]
        if correct in refs_by_split["test"]:
            correct_in_test += 1
        sid, idx = correct.rsplit("_", 1)
        if int(idx) != q["blank_position"]:
            wrongpos.append((correct, q["blank_position"]))
    print(
        "fitb",
        len(fitb),
        "answer_lengths",
        dict(anslens),
        "question_lengths",
        dict(qlens),
        "refs",
        len(all_refs),
        "unique_refs",
        len(set(all_refs)),
        "missing_refs",
        len(missing),
        "correct_in_test",
        correct_in_test,
        "correct_index_vs_blank_mismatch",
        len(wrongpos),
    )
    # compat
    lines = [
        x.split()
        for x in (root / "fashion_compatibility_prediction.txt").read_text().splitlines()
        if x.strip()
    ]
    labels = collections.Counter(x[0] for x in lines)
    lengths = collections.Counter(len(x) - 1 for x in lines)
    missingc = []
    positive_exact = 0
    positive = 0
    for x in lines:
        label = x[0]
        refs = x[1:]
        missingc += [i for i in refs if i not in all_items]
        if label == "1":
            positive += 1
            sids = {i.rsplit("_", 1)[0] for i in refs}
            if len(sids) == 1:
                sid = next(iter(sids))
                full = (
                    {f"{sid}_{it['index']}" for it in all_sets[sid][1]["items"]}
                    if sid in all_sets
                    else set()
                )
                if set(refs) == full:
                    positive_exact += 1
    print(
        "compat",
        len(lines),
        "labels",
        dict(labels),
        "length_dist",
        dict(sorted(lengths.items())),
        "missing_refs",
        len(missingc),
        "positive_exact_full_outfit",
        positive_exact,
        "positive_total",
        positive,
    )
    # sha256s
    for p in sorted(root.iterdir()):
        if p.is_file():
            print("sha256", p.name, hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == "__main__":
    run(main)
