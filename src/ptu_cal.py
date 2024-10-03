"""A basic module for PTU calibration."""
import time

import cv2
import kornia
import matplotlib.pyplot as plt
import numpy as np
import torch

import ptu.core
import wrapper

START_TILT = -20
END_TILT = 20
START_PAN = -15
END_PAN = 15

def main():
    ptuc = ptu.core.PtuController()
    reti = wrapper.ElpCameraRetina()

    # calibrate for tilt
    tilt_degrees = []
    del_y_pxs = []
    for degree in range(START_TILT, END_TILT+1):
        print('deg:', degree)
        orig, dely = capture_two_imgs(ptuc, reti, tilt_deg=degree, pan_deg=-150)
        del_y_px = get_del_y_sift(orig, dely)

        tilt_degrees.append(degree)
        del_y_pxs.append(del_y_px)

    # calibrate for pan
    # pan should have diff calibration for diff tilt angle, but skipped for now
    pan_degrees = []
    del_x_pxs = []
    for degree in range(START_PAN, END_PAN+1):
        print('deg:', degree)
        orig, dely = capture_two_imgs_dx(ptuc, reti, pan_deg=degree, tilt_deg=0)
        del_x_px = get_del_x_sift(orig, dely)

        pan_degrees.append(degree)
        del_x_pxs.append(del_x_px)

    # least square fit for pan calibration, as an example, copied from notebook
    coefs = np.column_stack((pan_degrees, np.ones_like(pan_degrees)))
    dep_var = -del_x_pxs  # negate for easier downstream compu
    ls_res, __, __, __ = np.linalg.lstsq(coefs, dep_var)
    print(ls_res, 'del X')
    plt.scatter(pan_degrees, dep_var)
    plt.plot(pan_degrees, ls_res[0]*np.asarray(pan_degrees)+ls_res[1], c='grey')
    pan_slope, pan_intercept = ls_res

    return tilt_degrees, del_y_pxs, pan_degrees, del_x_pxs

# linear calibration results, 2024-oct-03
# delta_pixel = slope * degree + intercept
TILT_SLOPE = 28.98246342
TILT_INTERCEPT = -2.52920662
PAN_SLOPE = 29.98246751
PAN_INTERCEPT = -7.84100644


def capture_two_imgs(ptuc, reti, tilt_deg, pan_deg=0):
    ptuc.pan(pan_deg)
    ptuc.tilt(0)
    time.sleep(2)
    img_src = reti.capture()
    orig_img = plt.imread(img_src)
    
    ptuc.tilt(tilt_deg)
    time.sleep(2)
    img_src = reti.capture()
    del_y_img = plt.imread(img_src)
    return orig_img, del_y_img

def capture_two_imgs_dx(ptuc, reti, pan_deg, tilt_deg=0):
    ptuc.tilt(tilt_deg)
    ptuc.pan(-135)  # starting pan; Markus desk good to SIFT :)
    time.sleep(2)
    img_src = reti.capture()
    orig_img = plt.imread(img_src)
    
    ptuc.pan(-135+pan_deg)
    time.sleep(2)
    img_src = reti.capture()
    del_x_img = plt.imread(img_src)
    return orig_img, del_x_img

def get_del_y_sift(orig_img, dely_img, max_size=500, use_closest=False):
    # crop img center regions
    h, w = dely_img.shape[:2]
    r = max_size // 2
    orig_band = orig_img[:, w//2-r:w//2+r+1, :].mean(-1).astype('uint8')
    dely_band = dely_img[:, w//2-r:w//2+r+1, :].mean(-1).astype('uint8')
    print(dely_band[:10,:10].dtype)
    # plot_two_imgs(orig_band, dely_band)

    # run sift
    orig_kp, orig_des = compu_sift(orig_band)
    dely_kp, dely_des = compu_sift(dely_band)
    print(orig_des.shape, dely_des.shape)
    # show_img(cv2.drawKeypoints(orig_band, orig_kp, orig_band, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS))

    # only use features in center region
    dely_kp_, center_idxs = [], []
    for i, kp in enumerate(dely_kp):
        if abs(kp.pt[1] - dely_band.shape[0]//2) <= r:
            dely_kp_.append(kp)
            center_idxs.append(i)
    dely_des_ = dely_des[center_idxs]
    print(len(dely_kp_), dely_des_.shape)

    dist, ind_pairs = calc_pairwise_dist(orig_des, dely_des_)
    print("pairwise dist", dist.shape, ind_pairs.shape)

    # prune
    top_kp_pairs, top_des_pairs = prune_feats(dist, ind_pairs, orig_kp, dely_kp_, orig_des, dely_des_)
    top_kp_coords = np.array([[*o_kp.pt, *y_kp.pt] for o_kp, y_kp in top_kp_pairs])

    mean_dely = np.mean(top_kp_coords[:, 3] - top_kp_coords[:, 1])
    print(mean_dely, "(mean)")

    if not use_closest:
        __, ax = plt.subplots(figsize=(12, 12))
        ax = plot_inlier_matches(ax, orig_band, dely_band, top_kp_coords)
        ax.scatter(orig_band.shape[1]+dely_band.shape[1]//2, dely_band.shape[0]//2)
        return mean_dely
    
    # use the feature closest to del_y center (w/ some viz)
    top_dely_kp_coords = np.array([[c[2], c[3]] for c in top_kp_coords])
    top_dely_kp_rel_coords = top_dely_kp_coords - [dely_band.shape[1]//2, dely_band.shape[0]//2]
    top_dely_kp_fixation_dists = np.linalg.norm(top_dely_kp_rel_coords, axis=-1)
    argmin = np.argmin(top_dely_kp_fixation_dists)
    print(top_dely_kp_fixation_dists[argmin], "@", argmin)
    fixn_kp_coords = top_kp_coords[argmin:argmin+1, :]
    # print(fixn_kp_coords)
    __, ax = plt.subplots(figsize=(12, 12))
    ax = plot_inlier_matches(ax, orig_band, dely_band, fixn_kp_coords)
    ax.scatter(orig_band.shape[1]+dely_band.shape[1]//2,dely_band.shape[0]//2)

    closest_dely = fixn_kp_coords[0, 3] - fixn_kp_coords[0, 1]
    print(closest_dely, "(closest)")
    return closest_dely

def get_del_x_sift(orig_img, delx_img, max_size=500, use_closest=False):
    # crop img center regions
    h, w = delx_img.shape[:2]
    r = max_size // 2
    lmost_px, rmost_px = w//2-r*4, w//2+r*4  # too much distortion beyond these
    orig_band = orig_img[h//2-r:h//2+r+1, lmost_px:rmost_px, :].mean(-1).astype('uint8')
    delx_band = delx_img[h//2-r:h//2+r+1, lmost_px:rmost_px, :].mean(-1).astype('uint8')

    # run sift
    orig_kp, orig_des = compu_sift(orig_band)
    delx_kp, delx_des = compu_sift(delx_band)
    print(orig_des.shape, delx_des.shape)
    # show_img(cv2.drawKeypoints(orig_band, orig_kp, orig_band, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS))

    # only use features in center region
    delx_kp_, center_idxs = [], []
    for i, kp in enumerate(delx_kp):
        if abs(kp.pt[1] - delx_band.shape[0]//2) <= r:
            delx_kp_.append(kp)
            center_idxs.append(i)
    delx_des_ = delx_des[center_idxs]
    print(len(delx_kp_), delx_des_.shape)

    dist, ind_pairs = calc_pairwise_dist(orig_des, delx_des_)
    print("pairwise dist", dist.shape, ind_pairs.shape)

    # prune
    top_kp_pairs, top_des_pairs = prune_feats(dist, ind_pairs, orig_kp, delx_kp_, orig_des, delx_des_)
    top_kp_coords = np.array([[*o_kp.pt, *x_kp.pt] for o_kp, x_kp in top_kp_pairs])

    mean_delx = np.mean(top_kp_coords[:, 2] - top_kp_coords[:, 0])
    print(mean_delx, "(mean)")

    if not use_closest:
        __, ax = plt.subplots(figsize=(12, 12))
        ax = plot_inlier_matches_v(ax, orig_band, delx_band, top_kp_coords)
        ax.scatter(orig_band.shape[1]//2, orig_band.shape[0]+delx_band.shape[0]//2)
        return mean_delx
    
    # use the feature closest to del_y center (w/ some viz)
    top_delx_kp_coords = np.array([[c[2], c[3]] for c in top_kp_coords])
    top_delx_kp_rel_coords = top_delx_kp_coords - [delx_band.shape[1]//2, delx_band.shape[0]//2]
    top_delx_kp_fixation_dists = np.linalg.norm(top_delx_kp_rel_coords, axis=-1)
    argmin = np.argmin(top_delx_kp_fixation_dists)
    print(top_delx_kp_fixation_dists[argmin], "@", argmin)
    fixn_kp_coords = top_kp_coords[argmin:argmin+1, :]
    # print(fixn_kp_coords)
    __, ax = plt.subplots(figsize=(12, 12))
    ax = plot_inlier_matches_v(ax, orig_band, delx_band, fixn_kp_coords)
    ax.scatter(orig_band.shape[1]//2, orig_band.shape[0]+delx_band.shape[0]//2)

    closest_delx = fixn_kp_coords[0, 2] - fixn_kp_coords[0, 0]
    print(closest_delx, "(closest)")
    return closest_delx


def compu_sift(img: np.ndarray):
    img_ = img.astype('uint8')
    sift = cv2.SIFT_create()
    kp = sift.detect(img_, None)
    kp, des = sift.compute(img_, kp)
    return kp, des

def calc_pairwise_dist(des_l, des_r, th=0.8):
    return kornia.feature.match_snn(torch.Tensor(des_l),
                                    torch.Tensor(des_r), th=th)

N_CLOSEST_FEATURES = 20

def prune_feats(dist, ind_pairs, kp_l, kp_r, des_l, des_r):
    __, top_k_closest = torch.topk(dist.squeeze(), N_CLOSEST_FEATURES, dim=0, largest=False)
    top_ind_pairs = ind_pairs[top_k_closest, :]

    top_kp_pairs = [(kp_l[il], kp_r[ir]) for il, ir in top_ind_pairs]
    top_des_pairs = [(des_l[il], des_r[ir]) for il, ir in top_ind_pairs]
    return top_kp_pairs, top_des_pairs

def plot_inlier_matches(ax, img1, img2, inliers):
    """
    Plot the matches between two images according to the matched keypoints
    :param ax: plot handle
    :param img1: left image
    :param img2: right image
    :inliers: x,y in the first image and x,y in the second image (Nx4)
    """
    res = np.hstack([img1, img2])
    ax.set_aspect('equal')
    ax.imshow(res, cmap='gray')
    
    ax.plot(inliers[:,0], inliers[:,1], '+r')
    ax.plot(inliers[:,2] + img1.shape[1], inliers[:,3], '+r')
    ax.plot([inliers[:,0], inliers[:,2] + img1.shape[1]],
            [inliers[:,1], inliers[:,3]], 'r', linewidth=0.4)
    ax.axis('off')

    return ax

def plot_inlier_matches_v(ax, img1, img2, inliers):
    """
    Plot the matches between two images according to the matched keypoints
    :param ax: plot handle
    :param img1: left image
    :param img2: right image
    :inliers: x,y in the first image and x,y in the second image (Nx4)
    """
    res = np.vstack([img1, img2])
    ax.set_aspect('equal')
    ax.imshow(res, cmap='gray')
    
    ax.plot(inliers[:,0], inliers[:,1], '+r')
    ax.plot(inliers[:,2], inliers[:,3] + img1.shape[0], '+r')
    ax.plot([inliers[:,0], inliers[:,2]],
            [inliers[:,1], inliers[:,3] + img1.shape[0]], 'r', linewidth=0.4)
    ax.axis('off')

    return ax


if __name__ == '__main__':
    main()
