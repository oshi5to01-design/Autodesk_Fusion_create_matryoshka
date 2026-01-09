import traceback

import adsk.core
import adsk.fusion


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct

        if not design:
            ui.messageBox("No active design", "Error")
            return

        rootComp = design.rootComponent

        # --- 設定値 ---
        target_body_name = "Body1"  # コピー元のボディ名
        scale_factor = 0.8  # 尺度 (0.8倍)
        move_x_mm = 200.0  # 移動距離 (mm)
        repeat_count = 10  # 繰り返し回数
        # ----------------

        move_x_cm = move_x_mm / 10.0

        # ターゲットのボディを探す
        target_body = rootComp.bRepBodies.itemByName(target_body_name)
        if not target_body:
            if rootComp.bRepBodies.count > 0:
                target_body = rootComp.bRepBodies.item(0)
            else:
                ui.messageBox(f"ボディが見つかりません: {target_body_name}")
                return

        # 形状操作マネージャーを取得
        brepMgr = adsk.fusion.TemporaryBRepManager.get()

        # 現在の形状をメモリ上にコピー（これを元に計算していく）
        current_temp_body = brepMgr.copy(target_body)

        # BaseFeature（履歴に依存しない形状の入れ物）を作成
        baseFeats = rootComp.features.baseFeatures
        baseFeat = baseFeats.add()
        baseFeat.startEdit()

        try:
            for i in range(repeat_count):
                # 1. 重心（バウンディングボックスの中心）を計算
                bbox = current_temp_body.boundingBox
                min_p = bbox.minPoint
                max_p = bbox.maxPoint

                cx = (min_p.x + max_p.x) * 0.5
                cy = (min_p.y + max_p.y) * 0.5
                cz = (min_p.z + max_p.z) * 0.5

                # 2. 行列を作成（縮小 + 移動）
                # A. 中心を原点へ移動
                mat_t1 = adsk.core.Matrix3D.create()
                mat_t1.translation = adsk.core.Vector3D.create(-cx, -cy, -cz)

                # B. 縮小
                mat_s = adsk.core.Matrix3D.create()
                mat_s.setCell(0, 0, scale_factor)
                mat_s.setCell(1, 1, scale_factor)
                mat_s.setCell(2, 2, scale_factor)

                # C. 元の位置へ戻す
                mat_t2 = adsk.core.Matrix3D.create()
                mat_t2.translation = adsk.core.Vector3D.create(cx, cy, cz)

                # D. 右へ移動
                mat_move = adsk.core.Matrix3D.create()
                mat_move.translation = adsk.core.Vector3D.create(move_x_cm, 0, 0)

                # 行列を合成: A -> B -> C -> D の順に適用
                mat_final = adsk.core.Matrix3D.create()
                mat_final.transformBy(mat_t1)
                mat_final.transformBy(mat_s)
                mat_final.transformBy(mat_t2)
                mat_final.transformBy(mat_move)

                # 3. 次の形状を作成
                # 現在の形状をコピーして、それに対して変形を行う
                next_temp_body = brepMgr.copy(current_temp_body)
                brepMgr.transform(next_temp_body, mat_final)

                # 4. デザイン空間に実体化（BaseFeatureの中に追加）
                rootComp.bRepBodies.add(next_temp_body, baseFeat)

                # 5. 次のループのために更新
                current_temp_body = next_temp_body

        finally:
            # 編集モードを終了（これを忘れるとFusionが操作不能になるので注意）
            baseFeat.finishEdit()

    except:
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))
